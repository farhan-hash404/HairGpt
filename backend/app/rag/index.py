"""The evidence index: ingestion and hybrid search.

    python -m app.rag.index            # sync SQL + (re)build the vector index if stale
    python -m app.rag.index --rebuild  # force a full rebuild

Layout:
    PostgreSQL / SQLite  system of record: documents, chunks, provenance, licence
    ChromaDB             dense vectors (all-MiniLM-L6-v2 via ONNX)
    BM25 (in memory)     sparse index, rebuilt from SQL when the corpus changes

Search = dense top-N  +  BM25 top-N  ->  Reciprocal Rank Fusion  ->  evidence-
grade prior  ->  optional LLM rerank  ->  per-document diversity cap.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.evidence import EvidenceChunk, EvidenceDocument
from app.rag.bm25 import BM25Index
from app.rag.chunking import chunk_sections, contextual_text
from app.rag.embeddings import EmbeddingProvider, cosine, get_embedding_provider
from app.rag.hybrid import RetrievedChunk, diversify, grade_prior, reciprocal_rank_fusion
from app.rag.sources import ALLOWED_SOURCES
from app.rag.vectorstore import ChromaVectorStore

log = logging.getLogger("hairgpt.rag.index")

CANDIDATES = 40  # per retriever, before fusion
# The evidence-grade prior did not help on the benchmark (RRF Hit@1 0.830
# without it vs 0.809 with it; see evaluation/results/fusion_ablation.md), so it
# is off by default. Grades are still shown to users with every citation.
GRADE_PRIOR_STRENGTH = 0.0
PER_DOC_CAP = 2
RERANK_FUSED = 15  # fused candidates shown to the reranker
RERANK_PER_RETRIEVER = 8  # plus each retriever's own top picks

Reranker = Callable[[str, list[RetrievedChunk]], list[RetrievedChunk]]


def load_corpus(path: str | Path) -> list[dict]:
    """Read the JSONL corpus, rejecting any document from a non-allowlisted source."""
    docs = []
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            doc = json.loads(line)
            if doc.get("source") not in ALLOWED_SOURCES:
                log.warning("corpus document %s REJECTED: source %r not allowlisted",
                            doc.get("doc_id"), doc.get("source"))
                continue
            docs.append(doc)
    return docs


def fingerprint(docs: list[dict]) -> str:
    joined = "|".join(sorted(f"{d['doc_id']}:{d['content_hash']}" for d in docs))
    return hashlib.sha256(joined.encode()).hexdigest()


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def sync_documents(db: Session, docs: list[dict]) -> dict[str, int]:
    """Upsert documents by stable key; re-chunk only those whose content changed.

    Documents that left the corpus are deleted, so a retracted or re-licensed
    source cannot linger in the index.
    """
    rows = db.scalars(select(EvidenceDocument)).all()
    wanted = {d["doc_id"] for d in docs}
    counts = {"added": 0, "updated": 0, "unchanged": 0, "removed": 0}

    # Legacy rows have no doc_key. They must be handled one by one: keyed into a
    # dict they would all collapse onto the single key None.
    existing: dict[str, EvidenceDocument] = {}
    for row in rows:
        if row.doc_key is None or row.doc_key not in wanted:
            db.delete(row)
            counts["removed"] += 1
        else:
            existing[row.doc_key] = row

    for doc in docs:
        row = existing.get(doc["doc_id"])
        if row is not None and row.content_hash == doc["content_hash"]:
            counts["unchanged"] += 1
            continue
        if row is None:
            row = EvidenceDocument(doc_key=doc["doc_id"])
            db.add(row)
            counts["added"] += 1
        else:
            row.chunks.clear()
            counts["updated"] += 1
        row.source = doc["source"]
        row.source_type = doc.get("source_type", "scraped")
        row.title = doc["title"][:300]
        row.url = doc["url"]
        row.publisher = doc.get("publisher", "")[:160]
        row.pub_date = _as_date(doc.get("pub_date"))
        row.evidence_grade = doc.get("evidence_grade", "")
        row.license = doc.get("license", "")
        row.license_url = doc.get("license_url", "")
        row.attribution = doc.get("attribution", "")
        row.content_hash = doc["content_hash"]
        row.meta = doc.get("meta") or {}
        row.domain = doc.get("domain", "hair")
        row.deprecated = False
        for chunk in chunk_sections(doc["sections"]):
            row.chunks.append(
                EvidenceChunk(
                    chunk_index=chunk.index,
                    section=chunk.section[:300],
                    text=chunk.text,
                    token_count=chunk.words,
                )
            )
    db.commit()
    return counts


@dataclass
class _ChunkRecord:
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

    def to_result(self) -> RetrievedChunk:
        return RetrievedChunk(**self.__dict__)


class RagIndex:
    """Owns the vector store, the embedder and the in-memory BM25 index."""

    def __init__(self, store: ChromaVectorStore, embedder: EmbeddingProvider, state_file: Path | None):
        self.store = store
        self.embedder = embedder
        self.state_file = state_file
        self._lock = threading.Lock()
        self._records: dict[str, _ChunkRecord] = {}
        self._bm25: BM25Index | None = None
        self._embeddings: dict[str, list[float]] = {}
        # Bumped whenever the SQL rows change, so caches keyed on it cannot serve
        # document ids from a previous sync (or from another database).
        self.generation = 0
        self.state: dict = {}
        if state_file and state_file.exists():
            self.state = json.loads(state_file.read_text(encoding="utf-8"))

    # -- ingestion --------------------------------------------------------------

    def ensure(self, db: Session, corpus_path: str | Path | None = None, force: bool = False) -> dict:
        """Bring SQL and the vector index in line with the corpus file."""
        with self._lock:
            docs = load_corpus(corpus_path or settings.corpus_file)
            fp = fingerprint(docs)
            counts = sync_documents(db, docs)
            model_changed = (
                self.state.get("embedding") != self.embedder.name
                or self.store.built_with != self.embedder.name
            )
            # Compare chunk-id SETS, not counts: a fresh database holding the same
            # corpus has the same number of chunks under different ids, and a
            # count check would leave dense search returning ids SQL never heard of.
            stale = (
                force
                or model_changed
                or self.state.get("fingerprint") != fp
                or self.store.all_ids() != self._chunk_ids(db)
            )
            if stale:
                if force or model_changed:
                    # Vectors from two embedding spaces must never be mixed.
                    self._build_dense(db)
                else:
                    self._reconcile_dense(db)
                self.state = {
                    "fingerprint": fp,
                    "embedding": self.embedder.name,
                    "chunks": self.store.count(),
                    "documents": len(docs),
                    "built_at": datetime.now(timezone.utc).isoformat(),
                }
                if self.state_file:
                    self.state_file.parent.mkdir(parents=True, exist_ok=True)
                    self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
            if stale or counts["added"] or counts["updated"] or counts["removed"]:
                self.generation += 1
            self._load_records(db)
            return {**counts, "rebuilt_vectors": stale, **self.state}

    @staticmethod
    def _chunk_ids(db: Session) -> set[str]:
        return {str(cid) for cid in db.scalars(select(EvidenceChunk.id)).all()}

    def _rows(self, db: Session):
        return db.execute(
            select(EvidenceChunk, EvidenceDocument)
            .join(EvidenceDocument, EvidenceChunk.document_id == EvidenceDocument.id)
            .where(EvidenceDocument.deprecated.is_(False))
            .order_by(EvidenceDocument.doc_key, EvidenceChunk.chunk_index)
        ).all()

    def _build_dense(self, db: Session) -> None:
        started = time.perf_counter()
        rows = self._rows(db)
        ids = [str(chunk.id) for chunk, _ in rows]
        texts = [contextual_text(doc.title, chunk.section, chunk.text) for chunk, doc in rows]
        embeddings = self.embedder.embed_many(texts) if texts else []
        metadatas = [
            {"doc_id": str(doc.id), "domain": doc.domain, "source": doc.source, "grade": doc.evidence_grade}
            for _, doc in rows
        ]
        self.store.reset()
        if ids:
            self.store.add(ids, embeddings, metadatas)
        self._embeddings = dict(zip(ids, embeddings))
        log.info("vector index rebuilt: %d chunks in %.1fs (%s)",
                 len(ids), time.perf_counter() - started, self.embedder.name)

    def _reconcile_dense(self, db: Session) -> None:
        """Incremental update: embed only chunks that are new, drop stale ones.

        Re-chunked documents get fresh chunk ids, so set differences between SQL
        and the vector store identify exactly what changed. A one-page corpus
        update then costs seconds instead of re-embedding everything.
        """
        started = time.perf_counter()
        rows = {str(chunk.id): (chunk, doc) for chunk, doc in self._rows(db)}
        stored = self.store.all_ids()
        stale_ids = sorted(stored - rows.keys())
        new_ids = sorted(rows.keys() - stored)
        if stale_ids:
            self.store.delete(stale_ids)
            for cid in stale_ids:
                self._embeddings.pop(cid, None)
        if new_ids:
            texts = [contextual_text(rows[c][1].title, rows[c][0].section, rows[c][0].text) for c in new_ids]
            embeddings = self.embedder.embed_many(texts)
            metadatas = [
                {"doc_id": str(rows[c][1].id), "domain": rows[c][1].domain,
                 "source": rows[c][1].source, "grade": rows[c][1].evidence_grade}
                for c in new_ids
            ]
            self.store.add(new_ids, embeddings, metadatas)
            self._embeddings.update(zip(new_ids, embeddings))
        log.info("vector index reconciled: +%d / -%d chunks in %.1fs",
                 len(new_ids), len(stale_ids), time.perf_counter() - started)

    def _load_records(self, db: Session) -> None:
        records: dict[str, _ChunkRecord] = {}
        for chunk, doc in self._rows(db):
            records[str(chunk.id)] = _ChunkRecord(
                chunk_id=str(chunk.id), doc_id=str(doc.id), doc_key=doc.doc_key or "",
                title=doc.title, section=chunk.section, text=chunk.text, url=doc.url,
                publisher=doc.publisher, source=doc.source, evidence_grade=doc.evidence_grade,
                license=doc.license, attribution=doc.attribution, domain=doc.domain,
            )
        self._records = records
        ids = list(records)
        self._bm25 = BM25Index(
            ids, [contextual_text(r.title, r.section, r.text) for r in records.values()]
        ) if ids else None

    @property
    def ready(self) -> bool:
        return self._bm25 is not None

    # -- search -----------------------------------------------------------------

    def _prefetch_embeddings(self, chunk_ids: list[str]) -> None:
        """Load stored vectors for BM25-only candidates in one round-trip."""
        missing = [cid for cid in chunk_ids if cid not in self._embeddings]
        if missing:
            self._embeddings.update(self.store.get_embeddings(missing))

    def search(
        self,
        query: str,
        domain: str = "hair",
        k: int = 5,
        method: str = "hybrid",
        reranker: Reranker | None = None,
        per_doc: int = PER_DOC_CAP,
        grade_strength: float = GRADE_PRIOR_STRENGTH,
    ) -> list[RetrievedChunk]:
        """Retrieve evidence chunks for a query.

        method: "hybrid" (default), "dense", or "bm25" — the latter two exist so
        the benchmark can measure what fusion actually buys.
        """
        if not self.ready or not query.strip():
            return []
        domains = [domain, "both"]
        allowed = {cid for cid, r in self._records.items() if r.domain in domains}
        qvec = self.embedder.embed(query)

        dense_ranking: list[str] = []
        similarity: dict[str, float] = {}
        if method in ("hybrid", "dense"):
            for hit in self.store.query(qvec, CANDIDATES, domains):
                if hit.chunk_id in allowed:
                    dense_ranking.append(hit.chunk_id)
                    similarity[hit.chunk_id] = hit.similarity

        sparse_ranking: list[str] = []
        if method in ("hybrid", "bm25"):
            sparse_ranking = [cid for cid, _ in self._bm25.search(query, CANDIDATES, allowed)]

        rankings = [r for r in (dense_ranking, sparse_ranking) if r]
        fused = reciprocal_rank_fusion(rankings)
        # BM25-only candidates still get a cosine similarity, used for abstention.
        self._prefetch_embeddings([cid for cid in fused if cid not in similarity])

        results: list[RetrievedChunk] = []
        for cid, rrf in fused.items():
            record = self._records.get(cid)
            if record is None:
                continue
            chunk = record.to_result()
            chunk.rrf = rrf
            chunk.dense_rank = dense_ranking.index(cid) + 1 if cid in similarity else None
            chunk.bm25_rank = sparse_ranking.index(cid) + 1 if cid in sparse_ranking else None
            if cid not in similarity:
                emb = self._embeddings.get(cid)
                similarity[cid] = round(cosine(qvec, emb), 4) if emb else 0.0
            chunk.similarity = similarity[cid]
            chunk.score = rrf * grade_prior(chunk.evidence_grade, grade_strength)
            results.append(chunk)

        results.sort(key=lambda c: c.score, reverse=True)
        if reranker is not None and results:
            # The window is the fused head PLUS each retriever's own top picks:
            # RRF can bury a chunk that only one retriever ranks first, and a
            # reranker can only rescue what it is shown.
            window_ids = {c.chunk_id for c in results[:RERANK_FUSED]}
            window_ids |= set(dense_ranking[:RERANK_PER_RETRIEVER])
            window_ids |= set(sparse_ranking[:RERANK_PER_RETRIEVER])
            head = [c for c in results if c.chunk_id in window_ids]
            tail = [c for c in results if c.chunk_id not in window_ids]
            try:
                results = reranker(query, head) + tail
            except Exception as exc:  # a reranker failure must never break retrieval
                log.warning("reranker failed (%s); keeping fused order", exc)
        return diversify(results, k, per_doc)


_default: RagIndex | None = None
_default_lock = threading.Lock()


def get_rag_index() -> RagIndex:
    global _default
    with _default_lock:
        if _default is None:
            embedder = get_embedding_provider()
            in_memory = settings.chroma_dir in ("", ":memory:")
            store = ChromaVectorStore(None if in_memory else settings.chroma_dir, embedder.name, embedder.dim)
            state = None if in_memory else Path(settings.chroma_dir) / "index_state.json"
            _default = RagIndex(store, embedder, state)
        return _default


def set_rag_index(index: RagIndex | None) -> None:
    """Swap the process-wide index (tests use an in-memory one)."""
    global _default
    with _default_lock:
        _default = index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        started = time.perf_counter()
        info = get_rag_index().ensure(db, force=args.rebuild)
        print(json.dumps(info, indent=2, default=str))
        print(f"done in {time.perf_counter() - started:.1f}s")
    finally:
        db.close()


if __name__ == "__main__":
    main()
