"""Public retrieval API used by recommendations, products and the Q&A agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.rag.hybrid import RetrievedChunk
from app.rag.index import Reranker, get_rag_index

__all__ = ["EvidenceRef", "is_supported", "retrieve", "search_chunks"]


@dataclass
class EvidenceRef:
    """A citable piece of evidence: one chunk, with the provenance to cite it."""

    id: str  # evidence_documents.id — what recommendations store in evidence_refs
    source: str
    title: str
    url: str
    publisher: str
    evidence_grade: str
    text: str
    score: float
    chunk_id: str = ""
    section: str = ""
    license: str = ""
    attribution: str = ""
    similarity: float = 0.0

    def to_public(self) -> dict:
        """Serialisable form for API responses (the full chunk text is the quote)."""
        data = asdict(self)
        data["quote"] = data.pop("text")
        return data


def _to_ref(chunk: RetrievedChunk) -> EvidenceRef:
    return EvidenceRef(
        id=chunk.doc_id,
        source=chunk.source,
        title=chunk.title,
        url=chunk.url,
        publisher=chunk.publisher,
        evidence_grade=chunk.evidence_grade,
        text=chunk.text,
        score=round(chunk.score, 5),
        chunk_id=chunk.chunk_id,
        section=chunk.section,
        license=chunk.license,
        attribution=chunk.attribution,
        similarity=chunk.similarity,
    )


def default_reranker() -> Reranker | None:
    if not settings.rag_cross_encoder:
        return None
    from app.rag.rerank import get_cross_encoder

    return get_cross_encoder()


def search_chunks(
    db: Session,
    query: str,
    domain: str = "hair",
    k: int | None = None,
    per_doc: int = 2,
    rerank: bool = True,
) -> list[RetrievedChunk]:
    index = get_rag_index()
    if not index.ready:
        index.ensure(db)
    reranker = default_reranker() if rerank else None
    return index.search(query, domain=domain, k=k or settings.rag_top_k, per_doc=per_doc, reranker=reranker)


def is_supported(chunk: RetrievedChunk | EvidenceRef, ce_logit: float | None = None) -> bool:
    """Does this evidence genuinely bear on the question?

    Refuses only when BOTH signals agree the match is weak. On the benchmark the
    cross-encoder under-scored lay phrasing ("why am I going bald at 25" logit
    -4.9) that cosine correctly judged relevant, so neither signal may veto
    alone.
    """
    weak_cosine = chunk.similarity < settings.rag_min_relevance
    if ce_logit is None and isinstance(chunk, RetrievedChunk):
        ce_logit = chunk.signals.get("cross_encoder_logit")
    if ce_logit is None:
        return not weak_cosine
    return not (weak_cosine and ce_logit < settings.rag_min_ce_logit)


def retrieve(
    db: Session,
    query: str,
    domain: str,
    top_k: int | None = None,
    supported_only: bool = False,
    rerank: bool = True,
) -> list[EvidenceRef]:
    """Best chunk per document, most relevant first.

    ``supported_only`` drops matches that fail the abstention rule, so a
    recommendation is emitted only when the corpus genuinely supports it rather
    than whenever retrieval returned *something*.
    """
    chunks = search_chunks(db, query, domain, k=top_k, per_doc=1, rerank=rerank)
    if supported_only:
        chunks = [c for c in chunks if is_supported(c)]
    return [_to_ref(c) for c in chunks]
