"""Official OTC drug labelling from DailyMed (US National Library of Medicine).

DailyMed lists hundreds of minoxidil labels, many from unknown resellers. Labels
are therefore PINNED to the originator brand (Rogaine, Kenvue) rather than taken
from the top of a search, so the corpus is authoritative and reproducible.

Sections are selected by their official LOINC section codes. The Directions
section (dosing) is excluded by code: HairGPT never states a dose.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from lxml import etree

from app.rag.sanitize import normalize
from app.rag.scraper.html_extract import Section
from app.rag.scraper.http import PoliteClient

log = logging.getLogger("hairgpt.scraper.dailymed")

API = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
NS = {"v3": "urn:hl7-org:v3"}

PINNED_LABELS = {
    "1b5e2860-6855-4a65-8bbc-e064172a1adf": "Men's Rogaine 5% minoxidil foam",
    "4d328537-b7f5-43cc-9837-c5a0c6c390f8": "Women's Rogaine 5% minoxidil foam",
}

# LOINC codes for OTC "Drug Facts" sections we keep.
INCLUDE_SECTIONS = {
    "55106-9": "Active ingredient",
    "55105-1": "Purpose",
    "34067-9": "Uses",
    "34071-1": "Warnings",
    "50570-1": "Do not use",
    "50569-3": "Ask a doctor before use",
    "50567-7": "When using this product",
    "50566-9": "Stop use and ask a doctor",
    "50565-1": "Keep out of reach of children",
    "60561-8": "Other information",
}
EXCLUDED_DOSING_CODE = "34068-7"  # Dosage & administration ("Directions")


@dataclass
class Label:
    setid: str
    title: str
    published: str
    sections: list[Section]

    @property
    def url(self) -> str:
        return f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={self.setid}"


def _own_text(section: etree._Element) -> str:
    """Text of a section's own <text> block, excluding nested sections."""
    text_el = section.find("v3:text", NS)
    if text_el is None:
        return ""
    return normalize(" ".join(text_el.itertext()))


def parse_spl(xml: bytes) -> tuple[str, list[Section]]:
    root = etree.fromstring(xml)
    title_el = root.find("v3:title", NS)
    title = normalize(" ".join(title_el.itertext())) if title_el is not None else ""

    sections: list[Section] = []
    for section in root.iter("{urn:hl7-org:v3}section"):
        code_el = section.find("v3:code", NS)
        code = code_el.get("code") if code_el is not None else None
        if code == EXCLUDED_DOSING_CODE or code not in INCLUDE_SECTIONS:
            continue
        text = _own_text(section)
        if len(text.split()) < 3:
            continue
        heading_el = section.find("v3:title", NS)
        heading = normalize(" ".join(heading_el.itertext())) if heading_el is not None else ""
        sections.append(Section(heading=heading or INCLUDE_SECTIONS[code], text=text))
    return title, sections


async def fetch_labels(client: PoliteClient) -> list[Label]:
    labels = []
    for setid, description in PINNED_LABELS.items():
        try:
            _, body = await client.get_text(f"{API}/spls/{setid}.xml")
            title, sections = parse_spl(body.encode("utf-8"))
        except Exception as exc:
            log.warning("could not fetch DailyMed label %s: %s", setid, exc)
            continue
        if sections:
            labels.append(Label(setid=setid, title=title or description, published="", sections=sections))
    return labels
