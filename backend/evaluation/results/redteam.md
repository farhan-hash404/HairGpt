# Red-team evaluation: evidence Q&A agent

Run `hardened` · model: `extractive (no LLM)` · corpus: 56 documents (`14faef3c34d8`) · 70 prompts from `evaluation/redteam_prompts.jsonl`.

Outputs are graded by `scripts/eval_redteam.py` with checks that are stricter than, and independent of, the agent's own policy filter.

| Metric | Value |
|---|---|
| Pass rate | 100.0% |
| Attack success rate (lower is better) | 0.0% |
| Over-refusal on benign questions | 0.0% |
| Harmless trigger-like wording blocked | 0.0% |
| Dose / diagnosis / treatment requests recognised | 100.0% |
| Outputs containing a dose, diagnosis or directive | 0 |
| Unverified answers shipped | 0 |
| Latency p50 / p95 | 1018 / 1450 ms |

| Category | Prompts | Pass rate |
|---|---|---|
| benign | 10 | 100% |
| benign_near_miss | 8 | 100% |
| crisis | 4 | 100% |
| diagnosis | 6 | 100% |
| dosing | 8 | 100% |
| emergency | 5 | 100% |
| fabrication_bait | 6 | 100% |
| off_topic | 5 | 100% |
| prescription | 6 | 100% |
| prompt_injection | 12 | 100% |

## Failures

None.
