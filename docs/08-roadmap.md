# HairGPT — Implementation Roadmap

## Guiding rule
Build the **MVP first**. Use honest, clearly-labeled mock CV inference where a trained model is unavailable; keep mock and real inference strictly separated; never present a mock as validated. Verify architecture against requirements before each stage.

## MVP (this build)
- [x] Architecture, DB schema, API contracts, wireframe, CV/RAG/safety docs
- [ ] Monorepo scaffold (backend + frontend + compose)
- [ ] AuthN/Z (JWT, RBAC), consent management
- [ ] Guided hair scanning (7 views) + image quality gate (synchronous, blocks bad images)
- [ ] CV abstraction layer + mock: segmentation, hairline, crown, scalp-visibility, apparent density
- [ ] Structured observations with confidence + provenance + is_mock
- [ ] Safety engine (deterministic red-flag override)
- [ ] Medical RAG (seed corpus, pgvector + fallback, concern-driven retrieval)
- [ ] Recommendation engine (evidence-gated, no prescriptions)
- [ ] LLM explanation layer (provider interface; distinguishes observation/inference/evidence/diagnosis)
- [ ] Treatment tracker + adherence
- [ ] Longitudinal timeline
- [ ] Before/after comparison with alignment + limitations
- [ ] "Why?" / "Evidence" / Doctor report
- [ ] Security: encrypted storage, export, delete, audit, consent
- [ ] Tests (safety rules, quality gate, prescription prohibition, confidence aggregation)

## Phase 2
- SkinGPT full (3-view capture, Skin Appearance Index, routines, ingredient conflict engine)
- Product intelligence with real OCR + ingredient DB
- Real CV backend (`CV_BACKEND=torch`) behind existing interfaces
- Real embeddings + expanded curated corpus
- CV worker pool (async jobs), presigned direct-to-S3 uploads at scale
- Clinician role UI + clinician-facing draft workflow

## Phase 3
- On-device pre-capture quality hints
- Calibrated uncertainty (temperature scaling / conformal prediction)
- Clinician portal, referral integrations
- Multi-language, accessibility audit, formal privacy/DPIA review

## Dataset & Evaluation (fairness is mandatory, not aggregate-only)
Training/eval pipelines must **stratify and report per subgroup**, never only aggregate:
- **Fitzpatrick I–VI** (skin tone)
- **age groups** (bands)
- **sex**
- **phone manufacturers** (sensor/ISP variation)
- **lighting conditions** (daylight/indoor warm/cool/mixed/low)
- **geography**

Requirements:
- Per-subgroup metrics: quality-gate FPR/FNR, segmentation IoU, landmark error, attribute MAE, calibration (ECE), plus worst-group vs best-group gap.
- A model is not promoted to `validated=True` until worst-group performance meets the bar and calibration is acceptable across subgroups.
- Datasets require consent, are de-identified, and images are never sold or used for advertising.
- Data cards + model cards documenting subgroup coverage, known gaps, and intended use are required artifacts.

## Definition of done for "real model" promotion
1. Stratified eval passes (above). 2. Calibration curve shipped. 3. Model card written. 4. `model_version` recorded on all outputs. 5. Rollback path to mock retained. Only then does `validated` flip to true for that capability.
