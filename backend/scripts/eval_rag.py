"""Benchmark the retrieval pipeline and log every variant to MLflow.

    python -m scripts.eval_rag                 # all variants
    python -m scripts.eval_rag --no-mlflow     # print only

Metrics are computed at DOCUMENT level — what matters for a citation is whether
the right source was retrieved, not which chunk of it:

    Hit@k      a relevant document appears in the top k
    MRR@10     mean reciprocal rank of the first relevant document
    Recall@5   fraction of all relevant documents found in the top 5
    AUROC      how well the top relevance signal separates in-scope questions
               from out-of-scope ones (the basis for abstaining)

Results are written to evaluation/results/rag_benchmark.{md,csv} so they can be
cited in the README without anyone needing to run MLflow.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from app.db.session import SessionLocal  # noqa: E402
from app.rag.index import get_rag_index  # noqa: E402
from app.rag.rerank import get_cross_encoder  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "evaluation" / "rag_benchmark.jsonl"
RESULTS = ROOT / "evaluation" / "results"


def load_benchmark() -> list[dict]:
    return [json.loads(line) for line in BENCHMARK.read_text(encoding="utf-8").splitlines() if line.strip()]


def auroc(positives: list[float], negatives: list[float]) -> float:
    """Probability a random in-scope query outscores a random out-of-scope one."""
    if not positives or not negatives:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in positives for n in negatives)
    return wins / (len(positives) * len(negatives))


def run_variant(index, items: list[dict], method: str, reranker, label: str) -> dict:
    per_query = []
    latencies = []
    for item in items:
        started = time.perf_counter()
        hits = index.search(item["query"], k=10, method=method, reranker=reranker, per_doc=1)
        latencies.append((time.perf_counter() - started) * 1000)
        ranked_docs = [h.doc_key for h in hits]
        relevant = set(item["relevant"])
        first = next((i + 1 for i, d in enumerate(ranked_docs) if d in relevant), None)
        top = hits[0] if hits else None
        signal = (
            top.signals.get("cross_encoder_logit", top.similarity) if top and reranker else
            (top.similarity if top else 0.0)
        )
        per_query.append({
            "variant": label,
            "id": item["id"],
            "kind": item["kind"],
            "query": item["query"],
            "first_relevant_rank": first,
            "top1": ranked_docs[0] if ranked_docs else "",
            "recall_at_5": (len(relevant & set(ranked_docs[:5])) / len(relevant)) if relevant else None,
            "relevance_signal": round(float(signal), 4),
            "latency_ms": round(latencies[-1], 1),
        })

    in_scope = [r for r in per_query if r["kind"] != "out_of_scope"]
    out_scope = [r for r in per_query if r["kind"] == "out_of_scope"]

    def hit(k: int) -> float:
        return sum(1 for r in in_scope if r["first_relevant_rank"] and r["first_relevant_rank"] <= k) / len(in_scope)

    metrics = {
        "hit_at_1": hit(1),
        "hit_at_3": hit(3),
        "hit_at_5": hit(5),
        "mrr_at_10": statistics.mean(1 / r["first_relevant_rank"] if r["first_relevant_rank"] else 0 for r in in_scope),
        "recall_at_5": statistics.mean(r["recall_at_5"] for r in in_scope),
        "abstain_auroc": auroc([r["relevance_signal"] for r in in_scope], [r["relevance_signal"] for r in out_scope]),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": sorted(latencies)[int(0.95 * (len(latencies) - 1))],
    }
    for kind in sorted({r["kind"] for r in in_scope}):
        subset = [r for r in in_scope if r["kind"] == kind]
        metrics[f"hit_at_3__{kind}"] = sum(
            1 for r in subset if r["first_relevant_rank"] and r["first_relevant_rank"] <= 3
        ) / len(subset)
    return {"label": label, "metrics": metrics, "rows": per_query}


def write_reports(results: list[dict], index) -> None:
    import pandas as pd

    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = [row for r in results for row in r["rows"]]
    pd.DataFrame(rows).to_csv(RESULTS / "rag_benchmark_per_query.csv", index=False)

    headline = ["hit_at_1", "hit_at_3", "hit_at_5", "mrr_at_10", "recall_at_5", "abstain_auroc", "latency_p50_ms"]
    lines = [
        "# Retrieval benchmark",
        "",
        f"Corpus: {index.state.get('documents')} documents, {index.state.get('chunks')} chunks. "
        f"Embeddings: `{index.embedder.name}`. Benchmark: `evaluation/rag_benchmark.jsonl` "
        f"({sum(1 for r in results[0]['rows'] if r['kind'] != 'out_of_scope')} in-scope + "
        f"{sum(1 for r in results[0]['rows'] if r['kind'] == 'out_of_scope')} out-of-scope questions). "
        "Metrics are document-level.",
        "",
        "| Variant | " + " | ".join(headline) + " |",
        "|---|" + "---|" * len(headline),
    ]
    for r in results:
        cells = []
        for key in headline:
            value = r["metrics"][key]
            cells.append(f"{value:.0f}" if key.startswith("latency") else f"{value:.3f}")
        lines.append(f"| {r['label']} | " + " | ".join(cells) + " |")

    kinds = sorted(k.split("__")[1] for k in results[0]["metrics"] if k.startswith("hit_at_3__"))
    lines += ["", "Hit@3 by question type:", "", "| Variant | " + " | ".join(kinds) + " |",
              "|---|" + "---|" * len(kinds)]
    for r in results:
        lines.append(f"| {r['label']} | " + " | ".join(f"{r['metrics'][f'hit_at_3__{k}']:.2f}" for k in kinds) + " |")

    best = results[-1]
    misses = [row for row in best["rows"] if row["kind"] != "out_of_scope" and
              (not row["first_relevant_rank"] or row["first_relevant_rank"] > 3)]
    lines += ["", f"Questions where `{best['label']}` missed the top 3:", ""]
    lines += [f"- `{m['id']}` {m['query']} — top result `{m['top1']}`, first relevant at rank "
              f"{m['first_relevant_rank'] or 'none'}" for m in misses] or ["- none"]
    (RESULTS / "rag_benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def log_to_mlflow(results: list[dict], index) -> None:
    import mlflow

    mlflow.set_tracking_uri(f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}")
    mlflow.set_experiment("hairgpt-rag-retrieval")
    for r in results:
        with mlflow.start_run(run_name=r["label"]):
            mlflow.log_params({
                "variant": r["label"],
                "embedding": index.embedder.name,
                "documents": index.state.get("documents"),
                "chunks": index.state.get("chunks"),
                "corpus_fingerprint": (index.state.get("fingerprint") or "")[:12],
            })
            mlflow.log_metrics({k: float(v) for k, v in r["metrics"].items()})
            mlflow.log_artifact(str(RESULTS / "rag_benchmark.md"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        index = get_rag_index()
        index.ensure(db)
    finally:
        db.close()

    items = load_benchmark()
    cross_encoder = get_cross_encoder()
    variants = [("bm25", "bm25", None), ("dense", "dense", None), ("hybrid-rrf", "hybrid", None)]
    if cross_encoder is not None:
        variants.append(("hybrid-rrf+cross-encoder", "hybrid", cross_encoder))

    results = []
    for label, method, reranker in variants:
        result = run_variant(index, items, method, reranker, label)
        results.append(result)
        m = result["metrics"]
        print(f"{label:26} Hit@1={m['hit_at_1']:.3f} Hit@3={m['hit_at_3']:.3f} MRR={m['mrr_at_10']:.3f} "
              f"R@5={m['recall_at_5']:.3f} AUROC={m['abstain_auroc']:.3f} p50={m['latency_p50_ms']:.0f}ms")

    write_reports(results, index)
    if not args.no_mlflow:
        log_to_mlflow(results, index)
    print(f"wrote {RESULTS / 'rag_benchmark.md'}")


if __name__ == "__main__":
    main()
