# Retrieval benchmark

Corpus: 56 documents, 1077 chunks. Embeddings: `onnx-all-MiniLM-L6-v2`. Benchmark: `evaluation/rag_benchmark.jsonl` (47 in-scope + 7 out-of-scope questions). Metrics are document-level.

| Variant | hit_at_1 | hit_at_3 | hit_at_5 | mrr_at_10 | recall_at_5 | abstain_auroc | latency_p50_ms |
|---|---|---|---|---|---|---|---|
| bm25 | 0.809 | 0.936 | 0.979 | 0.865 | 0.936 | 1.000 | 81 |
| dense | 0.851 | 0.915 | 0.936 | 0.890 | 0.887 | 1.000 | 76 |
| hybrid-rrf | 0.830 | 0.915 | 0.936 | 0.884 | 0.911 | 1.000 | 83 |
| hybrid-rrf+cross-encoder | 0.915 | 1.000 | 1.000 | 0.957 | 0.929 | 1.000 | 1198 |

Hit@3 by question type:

| Variant | lay | patient | spelling | technical |
|---|---|---|---|---|
| bm25 | 0.88 | 0.90 | 1.00 | 1.00 |
| dense | 0.88 | 0.95 | 1.00 | 0.88 |
| hybrid-rrf | 0.62 | 1.00 | 1.00 | 0.94 |
| hybrid-rrf+cross-encoder | 1.00 | 1.00 | 1.00 | 1.00 |

Questions where `hybrid-rrf+cross-encoder` missed the top 3:

- none
