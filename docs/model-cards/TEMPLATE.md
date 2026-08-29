# Model card — `<name>@<version>`

> A model card is **required** before a model may be marked validated. Copy this
> file to `docs/model-cards/<name>-<version>.md` and reference it from the
> manifest entry's `model_card` field.

## What it does
Capability (`segmenter` / `face` / `localizer` / …), what it takes in, what it
outputs, and the units or label space of that output.

## Intended use
The specific product surface this supports. State plainly that it produces
**image-based observations, not diagnoses**, and that it is not a medical device.

## Out of scope
Uses this model must not be put to. At minimum: diagnosis, triage without
clinician involvement, identity matching, and any use on populations it was not
evaluated on.

## Training data
Source, licence, consent basis, collection period, and size. Include the
**subgroup composition** — Fitzpatrick I–VI, age band, sex, device make,
lighting condition, geography — and say where coverage is thin. A model trained
mostly on one skin tone or one phone must say so here.

## Evaluation
Paste the stratified report from:

```bash
python -m scripts.evaluate_model --results results.json --model <name>
```

Report **per-subgroup metrics**, not just the aggregate. Record:

| | value | threshold |
|---|---|---|
| Worst-group score | | ≥ 0.70 |
| Worst-to-best gap | | ≤ 0.15 |
| Calibration error (ECE) | | ≤ 0.10 |
| Smallest subgroup n | | ≥ 30 |

## Known limitations and failure modes
Where it degrades: lighting, hair colour vs scalp contrast, occlusion, unusual
styling, wet hair, low resolution. Be specific — a limitation nobody can act on
is not a limitation, it is a disclaimer.

## Fairness assessment
Which subgroups perform worst, by how much, and what is being done about it. If
a gap is being accepted for now, say so explicitly and record who accepted it.

## Calibration
Reliability diagram or ECE, and whether temperature scaling / conformal
prediction was applied. The product presents confidence as a reason to trust a
result, so an overconfident model is more dangerous than a weak one.

## Rollback
The mock implementation this replaces, and how to revert (`CV_BACKEND=mock`, or
removing the manifest entry). A rollback path must exist for every deployed model.

## Sign-off
| Role | Name | Date |
|---|---|---|
| ML engineer | | |
| Clinical reviewer | | |
