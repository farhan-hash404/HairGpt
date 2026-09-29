"""Section-aware chunking.

Chunks never cross a section boundary, split on sentences rather than mid-way
through one, and overlap slightly so a fact that straddles two chunks is still
retrievable whole.

Each chunk also gets a *contextual header* — the document title and section —
that is indexed but not shown. A chunk reading "It can take up to 12 months to
work" is useless to BM25 and ambiguous to an embedding model; prefixed with
"Finasteride — Common questions" it retrieves correctly.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.sanitize import split_sentences

TARGET_WORDS = 170
OVERLAP_WORDS = 35
MIN_WORDS = 12


@dataclass
class Chunk:
    index: int
    section: str
    text: str

    @property
    def words(self) -> int:
        return len(self.text.split())


def _units(text: str) -> list[str]:
    """Sentences, but list items and short lines stay whole."""
    units: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- ") or len(line.split()) <= 25:
            units.append(line)
        else:
            units.extend(split_sentences(line))
    return units


def chunk_sections(sections: list[dict], target: int = TARGET_WORDS, overlap: int = OVERLAP_WORDS) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in sections:
        heading = section.get("heading", "")
        units = _units(section.get("text", ""))
        current: list[str] = []
        count = 0
        for unit in units:
            n = len(unit.split())
            if current and count + n > target:
                chunks.append(Chunk(len(chunks), heading, "\n".join(current)))
                # Carry trailing units forward as overlap.
                carry: list[str] = []
                carried = 0
                for prev in reversed(current):
                    carried += len(prev.split())
                    if carried > overlap:
                        break
                    carry.insert(0, prev)
                current, count = carry, sum(len(u.split()) for u in carry)
            current.append(unit)
            count += n
        if current:
            text = "\n".join(current)
            # A short tail is merged into the previous chunk of the same section.
            if len(text.split()) < MIN_WORDS and chunks and chunks[-1].section == heading:
                chunks[-1].text += "\n" + text
            elif len(text.split()) >= 4:
                chunks.append(Chunk(len(chunks), heading, text))
    return chunks


def contextual_text(title: str, section: str, text: str) -> str:
    """What gets embedded and BM25-indexed: header + body."""
    header = title if not section or section == title else f"{title} — {section}"
    return f"{header}\n{text}"
