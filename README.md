# HairGPT

**Hair and scalp analysis platform.** Not a chatbot — a clinically cautious tracking and explanation system built around one loop:

```
Analyze → Explain → Track → Recommend → Escalate
```

Seven guided views, an image-quality gate that refuses to analyse what it can't read, and a deterministic safety layer that can overrule the language model.

The pipeline is domain-parameterized and a second domain (skin) is implemented behind it, but the product ships **one domain deliberately** — see [*One domain, on purpose*](#one-domain-on-purpose).

> ### ⚠️ Clinical position — read this first
> HairGPT produces **image-based observations and AI inferences**. It is **not a medical device**, does **not diagnose**, and **never prescribes medication**.
> The computer-vision models shipped in this repository are **mock, non-validated heuristics**. Every value they produce is labeled `is_mock: true` in the API and `mock · not validated` in the UI. **Nothing here has clinical accuracy.** Do not use it to make health decisions.

---

## What's built

| Capability | Status |
|---|---|
| Architecture, DB schema, API contracts, wireframe, CV/RAG/safety docs | ✅ [`docs/`](docs/) |
| Auth (JWT + rotating refresh), RBAC, consent management | ✅ |
| Guided hair scanning — 7 views with live coaching | ✅ |
| Image-quality gate (blur / lighting / overexposure / distance / angle / scalp visibility) | ✅ blocks analysis |
| CV abstraction layer + mock segmentation, hairline, crown, density, scalp visibility | ✅ model-agnostic |
| Structured observations with confidence + provenance + `is_mock` | ✅ |
| Deterministic safety engine that overrides the LLM | ✅ |
| Pre-analysis symptom check feeding the safety engine | ✅ |
| Ghost-overlay capture + framing consistency score | ✅ |
| Clinical history intake + history-driven safety rules | ✅ |
| Shedding log with per-context trend analysis | ✅ |
| Model validation gate + stratified fairness harness | ✅ |
| Medical RAG (source allowlist, pgvector + portable fallback) | ✅ |
| Evidence-gated recommendation engine, structurally prescription-free | ✅ |
| LLM explanation layer (provider interface, output scrubber) | ✅ |
| Treatment tracker + adherence | ✅ |
| Longitudinal timeline with noise-aware trend reporting | ✅ |
| Before/after comparison — aligned overlay + difference map | ✅ |
| "Why?" / "Evidence" / Doctor report | ✅ |
| Encrypted storage, export, hard delete, audit log | ✅ |
| SkinGPT (3-view capture, Skin Appearance Index, routines) | 🔒 built, **not exposed** — see below |
| Product intelligence (OCR + ingredient conflicts) | ⚠️ partial — see Known limitations |
| Real CV backend (`CV_BACKEND=torch`) | ✅ runs; **no checkpoints ship** |
| Trained model weights | ❌ none — see Known limitations |

**90 backend tests** cover the clinical invariants. `npm run build` is clean with **0 npm vulnerabilities**.

---

## Setup

**Prerequisites:** Python 3.11+, Node 20+. PostgreSQL, S3 and any ML stack are **optional** — the MVP runs without them.

### 1. Backend

```bash
cd backend
python -m venv .venv
```

Activate it — `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (macOS/Linux) — then:

```bash
pip install -r requirements-dev.txt
```

(`requirements.txt` alone is the leaner runtime set the deployed API uses; `-dev` adds tests, MLflow and the evaluation tooling.)

Configure and initialize:

```bash
cp .env.example .env
```

```bash
python -m alembic upgrade head
```

Load the demo account (3 scans, treatments, 30 days of adherence):

```bash
python -m scripts.seed_demo
```

Run it:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs>

### 2. Frontend

```bash
cd frontend
npm install
```

```bash
npm run dev
```

Open <http://localhost:3000> and sign in with **demo@example.com** / **demopassword123**.

> `numpy` and `Pillow` are technically optional, but **install them** — without them the CV heuristics fall back to a deterministic hash-based stub that analyzes no real pixels.

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `HAIRGPT_ENV` | `dev` | `dev` auto-creates tables and seeds the corpus; `prod` does neither. |
| `SECRET_KEY` | dev value | JWT signing + IP hashing salt. **Must be changed in production.** |
| `ACCESS_TOKEN_TTL_MIN` / `REFRESH_TOKEN_TTL_DAYS` | `30` / `14` | Token lifetimes. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins. |
| `DATABASE_URL` | `sqlite:///./hairgpt.db` | Prod: `postgresql+psycopg://user:pass@host:5432/hairgpt` |
| `STORAGE_BACKEND` | `local` | `local` \| `s3` |
| `STORAGE_LOCAL_DIR` | `./storage` | Local encrypted object root. |
| `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION` | — | S3-compatible storage (MinIO, R2, S3). |
| `IMAGE_ENCRYPTION_KEY` | derived from `SECRET_KEY` | App-level envelope encryption key. **Set explicitly in production.** |
| `CV_BACKEND` | `mock` | `mock` \| `torch` |
| `CV_MODEL_DIR` | `./models` | Where the torch backend loads checkpoints. |
| `EMBEDDING_PROVIDER` | `hashing` | `hashing` \| `sentence_transformer` |
| `EMBEDDING_DIM` | `768` | Must match the pgvector column. |
| `RAG_TOP_K` | `5` | Retrieved evidence documents per query. |
| `LLM_PROVIDER` | `mock` | `mock` \| `anthropic` |
| `LLM_MODEL` | `claude-sonnet-5` | Model id when `LLM_PROVIDER=anthropic`. |
| `ANTHROPIC_API_KEY` | — | Required only for the `anthropic` provider. |
| `SAFETY_STRICT` | `true` | Fail-safe to a more cautious verdict on internal errors. |
| `ENABLE_SKIN_DOMAIN` | `false` | Exposes the skin domain. Off by design — see *One domain, on purpose*. |

Frontend: `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`) — the dev server proxies `/api/v1/*` to it.

---

## Database migrations

Alembic manages the schema. SQLite works for dev; PostgreSQL + pgvector for production.

```bash
python -m alembic upgrade head
```

Create a migration after changing models:

```bash
python -m alembic revision --autogenerate -m "describe the change"
```

Roll back one revision:

```bash
python -m alembic downgrade -1
```

Migrations that ship:
1. `fecd21625f17` — initial schema (18 tables).
2. `0002_pgvector` — **PostgreSQL only** (a no-op on SQLite): enables `vector` + `pgcrypto`, converts `evidence_chunks.embedding` to native `vector(768)`, and creates an HNSW cosine index.
3. `c107b3d3bd8d` — `framing_match` on image quality reports.
4. `314714c7d089` — clinical history and shedding log tables.
5. `5153637a15a3` — `validated` flag on observations (backfilled `false`, the safe default).

After running `0002_pgvector` on a fresh Postgres database, re-run the corpus ingest so embeddings land in the native column.

> Migrations own the schema. `scripts/seed_demo.py` deliberately does **not** create tables — it exits with instructions if you run it before migrating, so the dev database can't drift out of sync with Alembic.

---

## Model installation

The repository ships **no trained checkpoints** and runs fine without any.

**Enabling a real CV backend:**

1. `pip install torch numpy Pillow`
2. Copy [`backend/models/manifest.example.json`](backend/models/manifest.example.json) to `models/manifest.json` and point each entry at your checkpoint (TorchScript preferred — it carries its own architecture).
3. Set `CV_BACKEND=torch`.

Two guarantees govern this path:

- **Fallback is loud, never silent.** If torch is missing, a checkpoint is absent, or a manifest entry is malformed, the registry falls back to mock and logs the specific reason. It never passes a heuristic off as a trained model.
- **`is_mock` and `validated` are separate flags.** A real model that has not passed evaluation runs as `is_mock=false, validated=false` — its confidence is capped, the UI badges it *"unvalidated model"*, and the response carries a disclaimer. Only a passing evaluation record produces `validated=true`.

### The validation gate

`validated` is **re-derived from the recorded metrics every time the manifest loads**, so hand-editing `"passed": true` cannot promote a failing model — there is a test asserting exactly that. A model must clear all of:

| Gate | Threshold |
|---|---|
| Worst-subgroup score | ≥ 0.70 |
| Worst-to-best subgroup gap | ≤ 0.15 |
| Calibration error (ECE) | ≤ 0.10 |
| Smallest subgroup sample count | ≥ 30 |
| Subgroup axes reported | all six, mandatory |

Run it:

```bash
python -m scripts.evaluate_model --results results.json --model hair-scalp-seg
```

Exit code is 0 on pass, 1 on fail, so it drops straight into CI. To see the failure it exists to catch — a model with a healthy 0.790 aggregate that scores 0.621 on Fitzpatrick V–VI, and is refused:

```bash
python -m scripts.evaluate_model --demo-biased
```

A [model card](docs/model-cards/TEMPLATE.md) is required before validation.

**Real embeddings:** `pip install sentence-transformers`, then `EMBEDDING_PROVIDER=sentence_transformer`.
**Real OCR:** `pip install pytesseract` plus a system Tesseract install.
**Real LLM:** `pip install anthropic`, set `ANTHROPIC_API_KEY` and `LLM_PROVIDER=anthropic`.

---

## API documentation

Interactive OpenAPI at `/docs`; machine-readable at `/openapi.json`. Full contracts in [`docs/03-api-contracts.md`](docs/03-api-contracts.md). Base path `/api/v1`.

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`; `GET /auth/me` |
| Consent | `GET /auth/consents`, `POST /auth/consents` |
| Scans | `POST /scans`, `POST /scans/{id}/images/upload`, `POST /scans/{id}/analyze`, `GET /scans/{id}`, `GET /scans/{id}/result`, `GET /scans`, `GET /scans/{id}/images/{view}/content`, `GET /scans/{id}/doctor-report` |
| Explainability | `GET /analyses/{id}/why`, `GET /analyses/{id}/evidence` |
| Comparison | `POST /comparisons`, `GET /comparisons/{id}` |
| Timeline | `GET /timeline` |
| Treatments | `GET/POST /treatments`, `PATCH/DELETE /treatments/{id}`, `POST /treatments/{id}/adherence`, `GET /treatments/adherence/summary` |
| Products | `POST /products/scan`, `GET/POST /products`, `POST /products/recommend` |
| Account | `POST /account/export`, `DELETE /account` |

Two structural guarantees hold at the API layer:
- **There is no endpoint that prescribes.** `POST /treatments` records what a user or their clinician already decided.
- **`recommendations.is_prescription` is `false` by construction**, enforced by a database `CHECK` constraint — a direct SQL insert with `is_prescription=1` raises `IntegrityError`.

---

## Testing

```bash
cd backend && python -m pytest -q
```

30 tests, organized around the clinical invariants:

| File | What it locks down |
|---|---|
| `test_safety_engine.py` | Red flags force `refer`; low confidence forces `caution`; errors fail *safe*, not silent. |
| `test_safety_override_integration.py` | A red flag suppresses **all** cosmetic advice; sweeps every flag combination for prescriptions. |
| `test_recommendations_no_prescription.py` | Nothing is ever a prescription; care guidance must cite evidence. |
| `test_rag_source_allowlist.py` | Social-media sources are **rejected**; every retrieved ref is traceable. |
| `test_confidence_and_quality.py` | Overall confidence never exceeds the weakest stage; failed images carry retake guidance. |
| `test_imageio_dimensions.py` | Regression: dimensions reflect the original image, not the analysis thumbnail. |
| `test_api_flow.py` | Consent gate; low-quality images blocked; a self-reported red flag yields a referral-only result; image access is owner-only. |

Frontend:

```bash
cd frontend && npm run build
```

---

## One domain, on purpose

The pipeline, the CV interfaces, the safety engine and the RAG corpus are all
**domain-parameterized**, and the skin path is implemented end to end behind them:
`FaceAnalyzer` and its mock, four skin red-flag rules, a 3-view capture protocol,
the Skin Appearance Index, and skin evidence in the corpus. All of it is covered
by tests.

It is nonetheless **not exposed**. A shallow second product costs more credibility
than it adds surface area, and this project's argument is depth: one domain taken
all the way from guided capture through to a clinician handoff.

The cut is a config flag, not a deletion:

```bash
ENABLE_SKIN_DOMAIN=true
```

`POST /scans` with `domain: "skin"` returns `403 domain_not_enabled` while the flag
is off. The abstraction stays in the codebase deliberately — it is what demonstrates
the pipeline generalizes, rather than the generalization being speculative. Re-exposing
it needs the flag plus the two frontend routes (`/skin`, `/scan/skin`) restored from
git history.

---

## Known limitations

**Clinical**
1. **All CV output is mock and non-validated.** The heuristics (variance-of-Laplacian sharpness, luminance clustering, texture proxies) are not trained models and have no measured accuracy on any population. `is_mock: true` everywhere. The torch backend and validation gate are real and tested, but **no trained weights ship** — the gate is machinery waiting for a model, not evidence that one exists.
2. **Hair/scalp "segmentation" is luminance thresholding**, not semantic segmentation. It will behave very differently across hair colors and skin tones — light hair on light scalp is close to a worst case. **No fairness evaluation has been run.**
3. **"Density" is not follicular density.** It is a texture proxy, labeled `apparent`. No pixel-to-millimeter calibration exists, so no true measurement is possible.
4. **Distance checking is really resolution adequacy.** True distance needs a landmark model; a high-resolution photo taken from far away will pass. Documented in `imageio.py`.
5. **Most red flags come from self-report, not from vision.** Scarring, pustules, sudden patchy loss and facial swelling cannot be detected by the current CV stack, so the app asks the user directly in a pre-analysis safety check (a single "yes" forces a referral). This is honest and it works — but it means **the safety net depends on the user answering accurately**, and a user who doesn't recognize or report a sign will not be escalated. A real deployment should add trained detectors *in addition to* the questionnaire.
6. **The seed corpus is 12 short paraphrased summaries**, not the full guidelines. Sufficient to demonstrate grounding; not sufficient for real coverage.

**Technical**
7. **Analysis is synchronous** — a 7-view scan blocks the request. Production needs the worker pool the architecture anticipates.
8. **Alignment is centroid + spread normalization**, not feature-based registration. Alignment quality is honestly reported (~60% on the demo data) and gates comparison confidence. The ghost-overlay framing score is a *composition* proxy (8×8 luminance layout correlation) — it catches shifts and zooms, but is not true pose estimation and cannot detect head rotation about the vertical axis.
15. **The shedding log is self-reported and unverifiable.** Counts depend on hair length, wash frequency and how carefully someone counts. Trends are computed per context and suppressed when the change is within the data's own variability, but they remain indicative only.
16. **History-driven safety rules depend on accurate self-report.** They meaningfully widen the safety net — they are the only way the app currently sees thyroid disease, iron deficiency or drug-associated shedding — but someone who doesn't know or doesn't disclose a condition will not be escalated.
9. **Presigned uploads are stubbed** in local mode; the client posts through the API. S3 mode needs real presigned URL generation.
10. **The XOR dev fallback in `storage.py` is not encryption.** Install `cryptography` so Fernet is used, and set `IMAGE_ENCRYPTION_KEY`.
11. **Product OCR needs Tesseract.** Without it, `/products/scan` honestly returns `confidence: 0` and asks for manual entry rather than inventing ingredients. Barcode lookup and the ingredient database are not implemented.
12. **The difference map is a raw luminance diff** — it responds to lighting and pose as much as to real change, as its caption states.
13. **No rate limiting is enforced** yet, and refresh-token cleanup has no scheduled job.
14. **Tokens live in `localStorage`**, which is XSS-readable. Production should move to httpOnly cookies with CSRF protection.

---

## Production deployment

**1. Secrets and configuration**
Set `HAIRGPT_ENV=prod`, a strong random `SECRET_KEY`, and an explicit `IMAGE_ENCRYPTION_KEY` from a secret manager. In `prod` the app does *not* auto-create tables or auto-seed — run migrations and ingestion deliberately.

**2. Database** — managed PostgreSQL 15+ with `vector` and `pgcrypto`, encryption at rest, PITR backups, TLS-only connections. Run `alembic upgrade head`, then the corpus ingest.

**3. Storage** — a private S3-compatible bucket: block all public access, enable SSE (app-level envelope encryption is applied on top), versioning, and a lifecycle policy matching your retention commitment. Never make image URLs public.

**4. Backend** — containerize and run `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`. Terminate TLS at the load balancer, set HSTS, and restrict `CORS_ORIGINS` to your real origin. Add rate limiting at the edge. Split CV inference into its own worker pool (GPU optional) — the service interfaces make this a deployment change, not a code change.

**5. Frontend** — `npm run build` and deploy behind the same TLS origin. Set `NEXT_PUBLIC_API_BASE`, and a CSP that disallows inline scripts.

**6. Observability** — ship the audit log to durable append-only storage. Alert on: safety-verdict distribution shifts, quality-gate failure rate, CV fallback-to-mock warnings, and p95 analysis latency.

**7. Compliance — before any real users**
This is the part that is *not* optional. Depending on jurisdiction and claims, an app of this kind may be a regulated medical device. Before launch you need: a regulatory determination (FDA/UKCA/CE/MDR as applicable), a DPIA and lawful basis under GDPR (health data is special-category), HIPAA analysis if operating in the US with covered entities, a clinical safety case (e.g. DCB0129 in the UK), documented clinical review of the safety rules, and a published retention/deletion policy. **Do not deploy to real users on mock models.**

---

## Future model-training plan

**Phase 1 — data foundation.** Consented, de-identified capture with per-subject metadata for Fitzpatrick I–VI, age band, sex, device make, lighting condition, and geography. Dermatologist-annotated ground truth: hair/scalp masks, hairline and crown landmarks, trichoscopy-derived density where available, skin attribute ratings with inter-rater agreement. Publish a data card documenting coverage **and gaps**. Images are never sold or used for advertising.

**Phase 2 — models.** Hair/scalp segmentation (U-Net / SegFormer / DeepLabv3+); landmark model for alignment and region cropping (**never identity**); per-attribute skin regressors with calibrated uncertainty; a purpose-built quality gate trained on real retake decisions rather than heuristics.

**Phase 3 — stratified evaluation (mandatory).** Report per subgroup, never aggregate-only: quality-gate FPR/FNR, segmentation IoU, landmark error, attribute MAE, and calibration (ECE). Track the **worst-group vs best-group gap** as a release gate. Aggregate accuracy alone is not an acceptable result.

**Phase 4 — calibration and promotion.** Temperature scaling or conformal prediction so reported confidence is honest. A capability may only set `is_mock=False` / `validated=True` after: stratified eval passes the worst-group bar, a calibration curve ships, a model card is written, `model_version` is recorded on every output, and a rollback path to mock is retained.

**Phase 5 — clinical validation.** Prospective comparison against clinician assessment, powered per subgroup, with a pre-registered protocol — before any claim of clinical utility is made anywhere in the product.

---

## Repository layout

```
docs/                     8 design documents (architecture → roadmap)
backend/
  app/
    api/routers/          FastAPI endpoints
    core/                 config, security, audit
    cv/                   ★ CV abstraction: base.py (ABCs), registry.py, mock/, torch/
    db/                   portable Base (SQLite + PostgreSQL)
    llm/                  provider interface, prompts, output scrubber
    models/               SQLAlchemy ORM
    rag/                  embeddings, ingest (allowlist), retriever, seed corpus
    recommendations/      evidence-gated engine, prescription blocklist
    safety/               ★ rules.py + engine.py — deterministic override
    schemas/              Pydantic contracts
    services/             storage (encrypted), orchestrator (the pipeline)
  alembic/                migrations
  scripts/seed_demo.py    synthetic demo data
  tests/                  27 tests
frontend/
  src/app/                App Router pages
  src/components/         guided capture, confidence ring, Why/Evidence, compare panes
  src/lib/api.ts          typed API client
```

The two files that carry the clinical guarantees are [`backend/app/safety/engine.py`](backend/app/safety/engine.py) and [`backend/app/services/orchestrator.py`](backend/app/services/orchestrator.py) — the orchestrator runs safety **before** recommendations and the LLM, so suppressed content never reaches the model that writes the user-facing text.
