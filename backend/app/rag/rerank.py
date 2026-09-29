"""Rerankers: re-score fused candidates by reading query and passage together.

Why a reranker at all: the dense model and BM25 disagree often, and each is
right on different queries. On "when should I stop using minoxidil", BM25 ranks
the Rogaine label's "Stop use and ask a doctor" section first while the small
embedding model never finds it; on "anemia and hair loss", BM25 finds the NHS
iron-deficiency page and dense retrieval does not. RRF rewards chunks that
appear in *both* lists, so a chunk that one retriever is sure about can lose to
two lukewarm ones. A cross-encoder sees the query and passage jointly and can
tell which is actually relevant.

CrossEncoderReranker  ms-marco-MiniLM-L-6-v2 (int8 ONNX), local, free, deterministic
LLMReranker           listwise reranking by the configured LLM, when one exists
"""

from __future__ import annotations

import logging
import threading
from functools import lru_cache

import numpy as np

from app.rag.chunking import contextual_text
from app.rag.hybrid import RetrievedChunk

log = logging.getLogger("hairgpt.rag.rerank")

CROSS_ENCODER_REPO = "Xenova/ms-marco-MiniLM-L-6-v2"
MAX_TOKENS = 320


class CrossEncoderReranker:
    name = "cross-encoder-ms-marco-MiniLM-L-6-v2-int8"

    def __init__(self):
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        model_path = hf_hub_download(CROSS_ENCODER_REPO, "onnx/model_quantized.onnx")
        tokenizer_path = hf_hub_download(CROSS_ENCODER_REPO, "tokenizer.json")
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self._tokenizer.enable_padding()
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(model_path, options, providers=["CPUExecutionProvider"])
        self._inputs = {i.name for i in self._session.get_inputs()}
        self._lock = threading.Lock()

    def scores(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        encodings = self._tokenizer.encode_batch([(query, p) for p in passages])
        feed = {
            "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
        }
        if "token_type_ids" in self._inputs:
            feed["token_type_ids"] = np.array([e.type_ids for e in encodings], dtype=np.int64)
        with self._lock:  # ORT sessions are thread-safe, but keep CPU use predictable
            logits = self._session.run(None, feed)[0]
        return [float(x) for x in np.asarray(logits).reshape(-1)]

    def __call__(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        texts = [contextual_text(c.title, c.section, c.text) for c in candidates]
        logits = self.scores(query, texts)
        for chunk, logit in zip(candidates, logits):
            chunk.signals["cross_encoder_logit"] = round(logit, 3)
            # Rank by the RAW logit. An earlier version multiplied sigmoid(logit)
            # by an evidence-grade prior: relevant passages all score ~4.7-4.9,
            # which the sigmoid squashes to ~0.99, so the prior silently became
            # the tie-breaker and pushed reviews above NHS pages on plain patient
            # questions. The ablation (scripts/ablate_fusion.py) measured it:
            # Hit@1 0.915 on raw logits vs 0.766 with the prior.
            chunk.score = logit
            chunk.reranked = True
        return sorted(candidates, key=lambda c: c.score, reverse=True)


@lru_cache(maxsize=1)
def get_cross_encoder() -> CrossEncoderReranker | None:
    try:
        return CrossEncoderReranker()
    except Exception as exc:  # offline first run, missing onnxruntime, etc.
        log.warning("cross-encoder unavailable (%s); retrieval continues without reranking", exc)
        return None
