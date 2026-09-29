"""Extract clean, section-structured article text from publisher HTML.

Headings are preserved because they make both better chunks (a chunk that
knows it belongs to "Causes of hair loss" retrieves better) and better citations
(the UI can say which section of a page supports a claim).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime

from bs4 import BeautifulSoup, NavigableString, Tag

from app.rag.sanitize import normalize
from app.rag.sources import Publisher

log = logging.getLogger("hairgpt.scraper.extract")

_HEADINGS = {"h2": 2, "h3": 3, "h4": 4}
_TEXT_BLOCKS = {"p", "li", "dd", "dt", "blockquote"}
_SKIP_TAGS = {"script", "style", "nav", "aside", "figure", "form", "button", "noscript", "svg", "iframe"}
_SKIP_CLASS_FRAGMENTS = (
    "nhsuk-review-date", "nhsuk-back-link", "nhsuk-breadcrumb", "nhsuk-contents-list",
    "nhsuk-pagination", "nhsuk-feedback", "nhsuk-share", "mp-refs", "share", "rating",
)
_REVIEWED = re.compile(r"Page last reviewed:\s*(\d{1,2}\s+\w+\s+\d{4})", re.IGNORECASE)
# Page metadata that some NHS layouts render as an ordinary paragraph.
_REVIEW_LINE = re.compile(r"^(page last reviewed|next review due)\b", re.IGNORECASE)


@dataclass
class Section:
    heading: str
    text: str


@dataclass
class ExtractedPage:
    title: str
    sections: list[Section]
    last_reviewed: date | None


def _skippable(tag: Tag) -> bool:
    if tag.name in _SKIP_TAGS:
        return True
    classes = " ".join(tag.get("class", []))
    return any(fragment in classes for fragment in _SKIP_CLASS_FRAGMENTS)


def _dropped(heading: str, publisher: Publisher) -> bool:
    low = heading.lower()
    return any(fragment in low for fragment in publisher.drop_headings)


def _parse_reviewed(soup: BeautifulSoup) -> date | None:
    match = _REVIEWED.search(soup.get_text(" ", strip=True))
    if not match:
        return None
    try:
        reviewed = datetime.strptime(match.group(1), "%d %B %Y").date()
    except ValueError:
        return None
    # Sources make mistakes too: in 2026 the NHS dandruff page claimed it was
    # "last reviewed: 27 July 2029". A review date in the future is impossible,
    # so it is recorded as unknown rather than shown to users as provenance.
    if reviewed > date.today():
        log.warning("implausible future review date %s ignored", reviewed)
        return None
    return reviewed


def extract(html: str, publisher: Publisher) -> ExtractedPage:
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    title = normalize(h1.get_text(" ", strip=True)) if h1 else ""
    if not title and soup.title:
        title = normalize(soup.title.get_text(" ", strip=True).split("|")[0].split(" - ")[0])

    roots = soup.select(publisher.content_selector) if publisher.content_selector else []
    if not roots:
        roots = [soup.find("main") or soup.body]

    sections: list[Section] = []
    current_heading = title
    current: list[str] = []
    drop_level: int | None = None  # headings at or below this level are dropped
    seen_blocks: set[str] = set()

    def flush() -> None:
        text = "\n".join(current).strip()
        if text and drop_level is None:
            sections.append(Section(heading=current_heading, text=text))
        current.clear()

    def walk(node: Tag) -> None:
        nonlocal current_heading, drop_level
        for child in node.children:
            if isinstance(child, NavigableString) or not isinstance(child, Tag):
                continue
            if _skippable(child):
                continue
            if child.name in _HEADINGS:
                level = _HEADINGS[child.name]
                heading = normalize(child.get_text(" ", strip=True))
                flush()
                if drop_level is not None and level > drop_level:
                    continue  # a subheading inside a dropped section stays dropped
                drop_level = level if _dropped(heading, publisher) else None
                current_heading = heading
                continue
            if child.name in _TEXT_BLOCKS:
                if drop_level is not None:
                    continue
                # Nested lists are walked separately so items are not doubled.
                if child.find(["ul", "ol"]):
                    lead = normalize("".join(
                        str(t) for t in child.find_all(string=True, recursive=False)
                    ))
                    if lead:
                        current.append(lead)
                    walk(child)
                    continue
                text = normalize(child.get_text(" ", strip=True))
                if len(text) < 3 or text in seen_blocks or _REVIEW_LINE.match(text):
                    continue
                seen_blocks.add(text)
                current.append(("- " + text) if child.name == "li" else text)
                continue
            walk(child)

    for root in roots:
        walk(root)
    flush()

    sections = [s for s in sections if not _is_navigation(s, title)]
    return ExtractedPage(title=title, sections=sections, last_reviewed=_parse_reviewed(soup))


def _is_navigation(section: Section, title: str) -> bool:
    """Tab bars and in-page menus that sit above the first real heading.

    Deliberately narrow: a bare list of three or more very short items, with no
    lead sentence, before any heading. Real content lists ("See a GP if: ...")
    have a lead-in or live under a heading, so they survive.
    """
    if section.heading != title:
        return False
    lines = section.text.splitlines()
    return (
        len(lines) >= 3
        and all(line.startswith("- ") for line in lines)
        and all(len(line.split()) <= 7 for line in lines)
    )
