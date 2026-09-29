"""Embedding providers behind one interface, mirroring the CV and LLM layers.

The default is all-MiniLM-L6-v2 run through ONNX Runtime (the same model
ChromaDB ships with): real 384-dimensional semantic embeddings, CPU-only, and no
PyTorch in the serving image. The hashing provider is a deterministic fallback
that keeps unit tests fast and offline.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings

log = logging.getLogger("hairgpt.rag.embeddings")


class EmbeddingProvider(ABC):
    name: str
    dim: int

    @abstractmethod
    def embed_many(self, texts: list[str]) -> list[list[float]]: ...

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]


def _l2(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class HashingEmbedding(EmbeddingProvider):
    """Feature-hashing bag of words. Deterministic, dependency-free, lexical only."""

    name = "hashing"

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in re.findall(r"[a-z0-9]+", text.lower()):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0 if (h >> 1) & 1 else -1.0
            out.append(_l2(vec))
        return out


class OnnxMiniLMEmbedding(EmbeddingProvider):
    """all-MiniLM-L6-v2 via ONNX Runtime (downloaded once, ~80 MB)."""

    name = "onnx-all-MiniLM-L6-v2"
    dim = 384

    def __init__(self):
        # Hold ONE model instance. Chroma's DefaultEmbeddingFunction constructs a
        # fresh ONNXMiniLM_L6_V2 inside every __call__, reloading the weights and
        # tokenizer each time: ~480 ms per query and minutes to index the corpus.
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

        self._ef = ONNXMiniLM_L6_V2()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for start in range(0, len(texts), 64):
            batch = self._ef(texts[start : start + 64])
            out.extend(_l2([float(x) for x in vec]) for vec in batch)
        return out


class SentenceTransformerEmbedding(EmbeddingProvider):  # pragma: no cover - optional heavy dependency
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.name = model_name
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


@lru_cache(maxsize=4)
def get_embedding_provider(name: str | None = None) -> EmbeddingProvider:
    choice = name or settings.embedding_provider
    if choice == "hashing":
        return HashingEmbedding(settings.embedding_dim)
    if choice == "sentence_transformer":
        try:
            return SentenceTransformerEmbedding()
        except Exception as exc:  # pragma: no cover
            log.warning("sentence-transformers unavailable (%s); using ONNX MiniLM", exc)
    try:
        return OnnxMiniLMEmbedding()
    except Exception as exc:  # pragma: no cover - only without chromadb/onnxruntime
        log.warning("ONNX embeddings unavailable (%s); FALLING BACK to hashing embeddings", exc)
        return HashingEmbedding(settings.embedding_dim)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
