"""Ablation: how should dense, BM25 and the cross-encoder be combined?

The first benchmark showed each ranker is confidently wrong on DIFFERENT
questions: BM25 on lay phrasing, the dense model on short label text, and the
cross-encoder on a drug-name-dense review it over-scores. This script scores
the cross-encoder once per question, then evaluates fusion rules over the SAME
candidate pool so the comparison is fair.

    python -m scripts.ablate_fusion

With only 47 labelled questions, differences of one or two questions are
noise. The rule adopted should be the simplest one near the top, not the
maximum of many tuned knobs.
"""

from __future__ import annotations

import os
import statistics
from collections import defaultdict

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from app.db.session import SessionLocal  # noqa: E402
from app.rag.chunking import contextual_text  # noqa: E402
from app.rag.hybrid import grade_prior  # noqa: E402
from app.rag.index import CANDIDATES, RERANK_FUSED, RERANK_PER_RETRIEVER, get_rag_index  # noqa: E402
from app.rag.rerank import get_cross_encoder  # noqa: E402
from scripts.eval_rag import ROOT, load_benchmark  # noqa: E402

K = 60


def rrf(rankings: list[tuple[list[str], float]]) -> dict[str, float]:
    fused: dict[str, float] = defaultdict(float)
    for ranking, weight in rankings:
        for rank, cid in enumerate(ranking, start=1):
            fused[cid] += weight / (K + rank)
    return fused


def doc_ranking(scores: dict[str, float], records, prior: float) -> list[str]:
    best: dict[str, float] = {}
    for cid, score in scores.items():
        record = records[cid]
        adjusted = score * grade_prior(record.evidence_grade, prior)
        best[record.doc_key] = max(best.get(record.doc_key, float("-inf")), adjusted)
    return [d for d, _ in sorted(best.items(), key=lambda kv: kv[1], reverse=True)]


def metrics(ranked: list[str], relevant: set[str]) -> tuple[int | None, float]:
    first = next((i + 1 for i, d in enumerate(ranked) if d in relevant), None)
    recall5 = len(relevant & set(ranked[:5])) / len(relevant)
    return first, recall5


def main() -> None:
    db = SessionLocal()
    index = get_rag_index()
    index.ensure(db)
    db.close()
    ce = get_cross_encoder()
    items = [i for i in load_benchmark() if i["kind"] != "out_of_scope"]
    records = index._records
    allowed = {cid for cid, r in records.items() if r.domain in ("hair", "both")}

    cached = []
    for item in items:
        q = item["query"]
        qvec = index.embedder.embed(q)
        dense = [h.chunk_id for h in index.store.query(qvec, CANDIDATES, ["hair", "both"]) if h.chunk_id in allowed]
        sparse = [cid for cid, _ in index._bm25.search(q, CANDIDATES, allowed)]
        base = rrf([(dense, 1.0), (sparse, 1.0)])
        window = [cid for cid, _ in sorted(base.items(), key=lambda kv: kv[1], reverse=True)[:RERANK_FUSED]]
        window = list(dict.fromkeys(window + dense[:RERANK_PER_RETRIEVER] + sparse[:RERANK_PER_RETRIEVER]))
        logits = ce.scores(q, [contextual_text(records[c].title, records[c].section, records[c].text) for c in window])
        ce_rank = [c for c, _ in sorted(zip(window, logits), key=lambda kv: kv[1], reverse=True)]
        cached.append({"item": item, "dense": dense, "sparse": sparse, "ce": dict(zip(window, logits)), "ce_rank": ce_rank})
        print(".", end="", flush=True)
    print()

    configs = {
        "bm25": lambda c: rrf([(c["sparse"], 1.0)]),
        "rrf(dense,bm25)": lambda c: rrf([(c["dense"], 1.0), (c["sparse"], 1.0)]),
        "rrf(dense:0.5,bm25)": lambda c: rrf([(c["dense"], 0.5), (c["sparse"], 1.0)]),
        "cross-encoder only": lambda c: {cid: logit for cid, logit in c["ce"].items()},
        "rrf(bm25,ce)": lambda c: rrf([(c["sparse"], 1.0), (c["ce_rank"], 1.0)]),
        "rrf(dense,bm25,ce)": lambda c: rrf([(c["dense"], 1.0), (c["sparse"], 1.0), (c["ce_rank"], 1.0)]),
        "rrf(dense:0.5,bm25,ce)": lambda c: rrf([(c["dense"], 0.5), (c["sparse"], 1.0), (c["ce_rank"], 1.0)]),
    }

    rows = []
    for name, scorer in configs.items():
        for prior in (0.0, 0.5):
            if name == "cross-encoder only" and prior:
                continue  # a multiplicative prior on raw logits is not meaningful
            firsts, recalls = [], []
            for c in cached:
                ranked = doc_ranking(scorer(c), records, prior)
                first, recall5 = metrics(ranked, set(c["item"]["relevant"]))
                firsts.append(first)
                recalls.append(recall5)
            n = len(firsts)
            row = {
                "config": name,
                "grade_prior": prior,
                "hit_at_1": sum(1 for f in firsts if f == 1) / n,
                "hit_at_3": sum(1 for f in firsts if f and f <= 3) / n,
                "mrr_at_10": statistics.mean(1 / f if f and f <= 10 else 0 for f in firsts),
                "recall_at_5": statistics.mean(recalls),
            }
            rows.append(row)
            print(f"{name:26} prior={prior:.1f}  Hit@1={row['hit_at_1']:.3f}  Hit@3={row['hit_at_3']:.3f}  "
                  f"MRR={row['mrr_at_10']:.3f}  R@5={row['recall_at_5']:.3f}")

    import mlflow

    mlflow.set_tracking_uri(f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}")
    mlflow.set_experiment("hairgpt-rag-fusion-ablation")
    for row in rows:
        with mlflow.start_run(run_name=f"{row['config']} prior={row['grade_prior']}"):
            mlflow.log_params({"config": row["config"], "grade_prior": row["grade_prior"], "questions": len(cached)})
            mlflow.log_metrics({k: v for k, v in row.items() if k not in ("config", "grade_prior")})

    lines = ["# Fusion ablation", "", f"{len(cached)} in-scope benchmark questions; document-level metrics.", "",
             "| Fusion | Grade prior | Hit@1 | Hit@3 | MRR@10 | Recall@5 |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['config']} | {r['grade_prior']} | {r['hit_at_1']:.3f} | {r['hit_at_3']:.3f} | "
              f"{r['mrr_at_10']:.3f} | {r['recall_at_5']:.3f} |" for r in rows]
    (ROOT / "evaluation" / "results" / "fusion_ablation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
