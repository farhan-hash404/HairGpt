from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import ALLOWED_SOURCES, EvidenceChunk, EvidenceDocument
from app.rag.embeddings import get_embedding_provider
from app.rag.seed_corpus import SEED_DOCUMENTS

log = logging.getLogger("hairgpt.rag")


def _chunk(text: str, size: int = 512, overlap: int = 64) -> list[str]:
    words = text.split()
    if len(words) <= size:
        return [text]
    out, i = [], 0
    while i < len(words):
        out.append(" ".join(words[i : i + size]))
        i += size - overlap
    return out


def ingest_document(db: Session, doc: dict) -> EvidenceDocument | None:
    """Ingest one curated document. Rejects anything not on the source allowlist."""
    if doc["source"] not in ALLOWED_SOURCES:
        log.warning("RAG ingest REJECTED disallowed source: %s", doc.get("source"))
        return None

    emb = get_embedding_provider()
    ed = EvidenceDocument(
        source=doc["source"],
        title=doc["title"],
        url=doc.get("url", ""),
        publisher=doc.get("publisher", ""),
        evidence_grade=doc.get("evidence_grade", ""),
        domain=doc.get("domain", "hair"),
    )
    db.add(ed)
    db.flush()

    for i, chunk_text in enumerate(_chunk(doc["text"])):
        vec = emb.embed(f"{doc['title']} {chunk_text}")
        db.add(
            EvidenceChunk(
                document_id=ed.id,
                chunk_index=i,
                text=chunk_text,
                embedding=vec,
                token_count=len(chunk_text.split()),
            )
        )
    return ed


def seed_corpus(db: Session, force: bool = False) -> int:
    """Idempotently load the seed corpus. Returns number of documents ingested."""
    existing = db.scalar(select(EvidenceDocument).limit(1))
    if existing and not force:
        return 0
    count = 0
    for doc in SEED_DOCUMENTS:
        if ingest_document(db, doc) is not None:
            count += 1
    db.commit()
    log.info("RAG seed corpus ingested %d documents", count)
    return count
