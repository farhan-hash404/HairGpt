"""Peer-reviewed, open-access literature via the Europe PMC REST API.

Why Europe PMC and not NCBI E-utilities: NCBI's robots.txt disallows all
automated agents on the E-utilities host. Europe PMC mirrors the same PMC
open-access literature, permits API use, and — usefully — can filter by licence
in the query itself.

Only CC BY / CC0 articles are kept (see sources.EUROPEPMC_ALLOWED_LICENSES), so
every excerpt can be redistributed with attribution.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import quote

from lxml import etree

from app.rag.sanitize import normalize, strip_citation_markers
from app.rag.scraper.html_extract import Section
from app.rag.scraper.http import PoliteClient, RobotsDisallowed
from app.rag.sources import EUROPEPMC_ALLOWED_LICENSES, LiteratureTopic

log = logging.getLogger("hairgpt.scraper.europepmc")

API = "https://www.ebi.ac.uk/europepmc/webservices/rest"

# Back-matter that carries no clinical content.
_SKIP_SECTION_TITLES = re.compile(
    r"conflict|competing interest|funding|acknowledg|author contribution|data availability|"
    r"ethics|abbreviation|supplementary|reference|declaration|consent for publication|"
    r"disclosure|financial support",
    re.IGNORECASE,
)
# Elements whose text is dropped outright: citation markers, tables, figures, maths.
_DROP_ELEMENTS = ("xref", "table-wrap", "fig", "disp-formula", "inline-formula", "table", "graphic")

MAX_BODY_WORDS = 3500


@dataclass
class Article:
    pmcid: str
    title: str
    journal: str
    year: str
    authors: str
    doi: str | None
    license_key: str
    pub_types: list[str]
    sections: list[Section]

    @property
    def url(self) -> str:
        return f"https://europepmc.org/article/PMC/{self.pmcid}"

    @property
    def evidence_grade(self) -> str:
        types = " ".join(self.pub_types).lower()
        if "systematic" in types or "meta-analysis" in types:
            return "systematic_review"
        if "review" in types:
            return "narrative_review"
        return "primary_study"


def build_query(topic_query: str) -> str:
    return (
        f"({topic_query}) AND OPEN_ACCESS:y AND HAS_FT:y "
        'AND (LICENSE:"cc by" OR LICENSE:"cc0") '
        'AND (PUB_TYPE:"review" OR PUB_TYPE:"systematic-review") '
        "AND PUB_YEAR:[2015 TO 2026]"
    )


def on_topic(title: str, topic: LiteratureTopic) -> bool:
    """Second relevance gate, applied to the fetched title itself."""
    low = title.lower()
    return any(term in low for term in topic.title_terms)


async def search(client: PoliteClient, topic: LiteratureTopic, limit: int) -> list[dict]:
    """Most-cited open-access reviews whose TITLE is about the topic."""
    query = quote(build_query(topic.title_query))
    url = f"{API}/search?query={query}&format=json&resultType=core&pageSize={limit * 4}&sort=CITED%20desc"
    data = await client.get_json(url)
    results = data.get("resultList", {}).get("result", [])
    kept = []
    for item in results:
        lic = (item.get("license") or "").lower().strip()
        if lic not in EUROPEPMC_ALLOWED_LICENSES or not item.get("pmcid"):
            continue
        if not on_topic(item.get("title", ""), topic):
            log.info("off-topic title rejected: %s", item.get("title", "")[:90])
            continue
        kept.append(item)
        if len(kept) >= limit:
            break
    return kept


def _text(el: etree._Element) -> str:
    for tag in _DROP_ELEMENTS:
        for bad in el.iter(tag):
            parent = bad.getparent()
            if parent is None:
                continue
            # Preserve the tail text that follows a removed element.
            if bad.tail:
                prev = bad.getprevious()
                if prev is not None:
                    prev.tail = (prev.tail or "") + bad.tail
                else:
                    parent.text = (parent.text or "") + bad.tail
            parent.remove(bad)
    return strip_citation_markers(normalize(" ".join(el.itertext())))


def parse_jats(xml: bytes) -> tuple[str, list[Section]]:
    """Return (title, sections) from a JATS full-text document."""
    root = etree.fromstring(xml)
    title_el = root.find(".//article-meta/title-group/article-title")
    title = _text(title_el) if title_el is not None else ""

    sections: list[Section] = []
    abstract = root.find(".//article-meta/abstract")
    if abstract is not None:
        paragraphs = [_text(p) for p in abstract.iter("p")]
        text = "\n".join(p for p in paragraphs if p)
        if text:
            sections.append(Section(heading="Abstract", text=text))

    body = root.find(".//body")
    words = 0
    if body is not None:
        for sec in body.iter("sec"):
            sec_title_el = sec.find("title")
            heading = _text(sec_title_el) if sec_title_el is not None else "Body"
            if _SKIP_SECTION_TITLES.search(heading):
                continue
            # Only direct paragraphs; nested <sec> elements are visited by iter().
            paragraphs = [_text(p) for p in sec.findall("p")]
            text = "\n".join(p for p in paragraphs if len(p.split()) >= 8)
            if not text:
                continue
            count = len(text.split())
            if words + count > MAX_BODY_WORDS:
                break
            words += count
            sections.append(Section(heading=heading, text=text))
    return title, sections


async def fetch_article(client: PoliteClient, meta: dict) -> Article | None:
    pmcid = meta["pmcid"]
    try:
        _, body = await client.get_text(f"{API}/{pmcid}/fullTextXML")
    except RobotsDisallowed:
        log.warning("robots.txt disallows full text for %s; skipping", pmcid)
        return None
    except Exception as exc:  # network or HTTP error for one article
        log.warning("could not fetch %s: %s", pmcid, exc)
        return None
    try:
        title, sections = parse_jats(body.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        log.warning("unparseable JATS for %s: %s", pmcid, exc)
        return None
    if not sections:
        return None

    journal = ((meta.get("journalInfo") or {}).get("journal") or {}).get("title", "")
    pub_types = (meta.get("pubTypeList") or {}).get("pubType", [])
    return Article(
        pmcid=pmcid,
        title=title or meta.get("title", ""),
        journal=journal,
        year=str(meta.get("pubYear", "")),
        authors=meta.get("authorString", ""),
        doi=meta.get("doi"),
        license_key=(meta.get("license") or "").lower().strip(),
        pub_types=pub_types if isinstance(pub_types, list) else [pub_types],
        sections=sections,
    )
