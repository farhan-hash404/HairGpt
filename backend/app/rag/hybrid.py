"""Rank fusion and post-processing for hybrid retrieval."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.rag.sources import EVIDENCE_GRADES

RRF_K = 60  # the constant from Cormack et al. (2009); robust across tasks


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    doc_key: str
    title: str
    section: str
    text: str
    url: str
    publisher: str
    source: str
    evidence_grade: str
    license: str
    attribution: str
    domain: str
    dense_rank: int | None = None
    bm25_rank: int | None = None
    similarity: float = 0.0  # cosine to the query; used for abstention
    rrf: float = 0.0
    score: float = 0.0
    reranked: bool = False
    signals: dict = field(default_factory=dict)


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """Fuse ranked id lists. Scores depend only on rank, which is why RRF works
    for combining cosine similarities and BM25 scores that share no scale."""
    fused: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            fused[item] += 1.0 / (k + rank)
    return dict(fused)


def grade_prior(grade: str, strength: float) -> float:
    """Multiplicative prior favouring stronger evidence; strength=0 disables it."""
    weight = EVIDENCE_GRADES.get(grade, 0.6)
    return 1.0 + strength * (weight - 0.8)


def diversify(chunks: list[RetrievedChunk], k: int, per_doc: int) -> list[RetrievedChunk]:
    """Keep ranking order but cap chunks per document, so one long review cannot
    fill every slot."""
    out: list[RetrievedChunk] = []
    taken: dict[str, int] = defaultdict(int)
    for chunk in chunks:
        if taken[chunk.doc_id] >= per_doc:
            continue
        taken[chunk.doc_id] += 1
        out.append(chunk)
        if len(out) >= k:
            break
    return out
