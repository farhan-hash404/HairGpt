from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.evidence import EvidenceChunk, EvidenceDocument
from app.rag.embeddings import cosine, get_embedding_provider

# Grade weighting for reranking (higher = stronger evidence).
_GRADE_WEIGHT = {
    "systematic_review": 1.0,
    "guideline": 0.9,
    "regulatory_label": 0.85,
    "expert_review": 0.7,
    "peer_reviewed": 0.8,
}


@dataclass
class EvidenceRef:
    id: str
    source: str
    title: str
    url: str
    publisher: str
    evidence_grade: str
    text: str
    score: float


def retrieve(db: Session, query: str, domain: str, top_k: int | None = None) -> list[EvidenceRef]:
    """Concern-driven retrieval over the curated corpus.

    The query is built from OBSERVED CONCERNS, never from the raw image. Uses
    pgvector in production; a portable in-Python cosine works everywhere for dev.
    """
    top_k = top_k or settings.rag_top_k
    emb = get_embedding_provider()
    qvec = emb.embed(query)

    stmt = (
        select(EvidenceChunk, EvidenceDocument)
        .join(EvidenceDocument, EvidenceChunk.document_id == EvidenceDocument.id)
        .where(EvidenceDocument.deprecated.is_(False))
        .where(EvidenceDocument.domain.in_([domain, "both"]))
    )
    rows = db.execute(stmt).all()

    scored: list[EvidenceRef] = []
    for chunk, doc in rows:
        sim = cosine(qvec, chunk.embedding or [])
        weight = _GRADE_WEIGHT.get(doc.evidence_grade, 0.6)
        final = sim * (0.6 + 0.4 * weight)  # rerank by grade
        scored.append(
            EvidenceRef(
                id=str(doc.id),
                source=doc.source,
                title=doc.title,
                url=doc.url,
                publisher=doc.publisher,
                evidence_grade=doc.evidence_grade,
                text=chunk.text,
                score=round(final, 4),
            )
        )

    scored.sort(key=lambda r: r.score, reverse=True)
    # Deduplicate by document, keep best chunk per doc.
    seen: set[str] = set()
    out: list[EvidenceRef] = []
    for r in scored:
        if r.id in seen:
            continue
        seen.add(r.id)
        out.append(r)
        if len(out) >= top_k:
            break
    return out
