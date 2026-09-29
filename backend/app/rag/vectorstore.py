"""Dense vector index on ChromaDB.

Embeddings are computed by our own EmbeddingProvider and passed in explicitly,
so the model is swappable and the benchmark measures exactly what serves. The
collection records which model built it; a mismatch forces a rebuild instead of
silently comparing vectors from two different embedding spaces.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import chromadb

log = logging.getLogger("hairgpt.rag.vectorstore")

COLLECTION = "hairgpt_evidence"


@dataclass
class DenseHit:
    chunk_id: str
    similarity: float  # cosine similarity, higher is closer


class ChromaVectorStore:
    def __init__(self, path: str | None, embedding_name: str, dim: int):
        # path=None gives an in-memory client (tests); otherwise a persistent one.
        self._client = chromadb.PersistentClient(path=path) if path else chromadb.EphemeralClient()
        self.embedding_name = embedding_name
        self.dim = dim
        self._collection = self._client.get_or_create_collection(
            COLLECTION,
            metadata={"hnsw:space": "cosine", "embedding_model": embedding_name, "dim": dim},
            embedding_function=None,
        )

    @property
    def built_with(self) -> str | None:
        return (self._collection.metadata or {}).get("embedding_model")

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        try:
            self._client.delete_collection(COLLECTION)
        except Exception:  # collection may not exist yet
            pass
        self._collection = self._client.get_or_create_collection(
            COLLECTION,
            metadata={"hnsw:space": "cosine", "embedding_model": self.embedding_name, "dim": self.dim},
            embedding_function=None,
        )

    def add(self, ids: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
        for start in range(0, len(ids), 256):
            end = start + 256
            self._collection.add(
                ids=ids[start:end],
                embeddings=embeddings[start:end],
                metadatas=metadatas[start:end],
            )

    def all_ids(self) -> set[str]:
        return set(self._collection.get(include=[])["ids"])

    def delete(self, ids: list[str]) -> None:
        for start in range(0, len(ids), 256):
            self._collection.delete(ids=ids[start : start + 256])

    def get_embeddings(self, ids: list[str]) -> dict[str, list[float]]:
        if not ids:
            return {}
        result = self._collection.get(ids=ids, include=["embeddings"])
        return {i: [float(x) for x in e] for i, e in zip(result["ids"], result["embeddings"])}

    def query(self, embedding: list[float], k: int, domains: list[str] | None = None) -> list[DenseHit]:
        if self.count() == 0:
            return []
        where = {"domain": {"$in": domains}} if domains else None
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(k, self.count()),
            where=where,
            include=["distances"],
        )
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        # Chroma's cosine "distance" is 1 - cosine similarity.
        return [DenseHit(chunk_id=i, similarity=round(1.0 - float(d), 4)) for i, d in zip(ids, distances)]
