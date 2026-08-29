from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

from app.core.config import settings


class EmbeddingProvider(ABC):
    dim: int

    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class HashingEmbedding(EmbeddingProvider):
    """Dependency-free deterministic embedding (feature hashing + L2 norm).

    Lets RAG run with NO ML stack. Quality is modest but retrieval is functional
    and reproducible. Swap for SentenceTransformerEmbedding in production.
    """

    def __init__(self, dim: int | None = None):
        self.dim = dim or settings.embedding_dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 1) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class SentenceTransformerEmbedding(EmbeddingProvider):  # pragma: no cover - optional
    """Real embedding backend. Enabled via EMBEDDING_PROVIDER=sentence_transformer."""

    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()


def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider == "sentence_transformer":
        try:
            return SentenceTransformerEmbedding()
        except Exception:
            # Loud-ish fallback keeps RAG working; production should install the model.
            return HashingEmbedding()
    return HashingEmbedding()


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
