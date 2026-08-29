# HairGPT — System Architecture

> **Clinical stance:** HairGPT is a *wellness and tracking* tool that produces **image-based observations and AI inferences**, not medical diagnoses. It never prescribes prescription medication, never fabricates measurements, and always distinguishes *visual observation → AI inference → medical evidence → clinician diagnosis*. A deterministic safety layer can override the LLM at any time.

## 1. Core principle

```
Analyze → Explain → Track → Recommend → Escalate
```

Two subsystems share one platform, one pipeline, one safety layer:

- **HairGPT** — hair & scalp analysis (front hairline, temples, top, crown, sides, back)
- **SkinGPT** — face & skin analysis (front, left, right)

## 2. Request pipeline (canonical flow)

Raw medical images are **never** the primary diagnostic mechanism sent to an LLM. Images are turned into *structured observations* by deterministic CV services first; the LLM only ever reasons over structured, confidence-tagged JSON plus retrieved evidence.

```
Frontend (Next.js)
   │  guided capture, quality preview, consent
   ▼
FastAPI (API gateway, auth, authz, audit)
   │  presigned upload → object storage; job orchestration
   ▼
CV Services  (ImageQualityGate → Segmentation → Localization → Metrics)
   │  emits StructuredObservation[] each with a ConfidenceScore
   ▼
Structured Observations  (typed, versioned, model-provenance tagged)
   │
   ├──► Medical RAG  (retrieve evidence for the observed concerns)
   │
   ▼
Safety Engine  (deterministic rules; can HARD-OVERRIDE everything downstream)
   │   red flags? → suppress cosmetic advice, force clinician referral
   ▼
Recommendation Engine  (evidence-gated care guidance, product/ingredient logic)
   │
   ▼
LLM  (explanation & phrasing ONLY, constrained by safety + evidence context)
   │   input = observations + evidence + safety verdict + recommendations
   ▼
Structured Response  (observation / reasoning / confidence / evidence / limitations)
```

**Key invariant:** the LLM is a *narrator and organizer*, not a diagnostician. If the Safety Engine returns `refer`, the LLM prompt is stripped of any cosmetic/self-treatment content and instructed to produce only a referral message. The Recommendation Engine will not emit prescription drugs under any code path.

## 3. Component responsibilities

| Layer | Tech | Responsibility |
|---|---|---|
| Web app | Next.js 14 (App Router), TS, Tailwind, shadcn/ui | Guided capture, dashboards, timeline, compare, treatment tracker, "Why?"/"Evidence" |
| API | FastAPI, Pydantic v2 | AuthN/Z, presigned uploads, orchestration, audit, export/delete |
| CV services | PyTorch / OpenCV / transformers behind interfaces | Quality gate, segmentation, localization, metrics — **replaceable** |
| Observations | Pydantic models + Postgres | Typed, versioned CV outputs with confidence + provenance |
| RAG | pgvector + embedding interface | Evidence retrieval from curated corpus (AAD/FDA/NICE/NHS/reviews) |
| Safety | Pure-Python rules engine | Deterministic red-flag detection & override |
| Recommendations | Rules + evidence gating | Care guidance, ingredient compatibility, product intelligence |
| LLM | Provider interface (Anthropic default) | Constrained explanation generation |
| Data | PostgreSQL + pgvector | Users, scans, observations, treatments, evidence, audit |
| Storage | S3-compatible (MinIO/S3) | Encrypted images; server-side + app-level envelope encryption |

## 4. Model-agnostic CV design

No CV architecture is hard-coded. Every capability is an ABC with:
- a **mock** implementation (deterministic, clearly labeled `validated=False`, ships by default), and
- a **real** implementation slot (loads a trained checkpoint when configured).

Selection is by config/env (`CV_BACKEND=mock|torch`). See [`05-cv-abstraction.md`](05-cv-abstraction.md). The same interface exists for embeddings and the LLM so all three are swappable.

## 5. Confidence everywhere

Every stage emits a `ConfidenceScore { value: 0..1, basis, method }`:
image quality, segmentation, hairline detection, density/scalp-visibility, skin analysis, and an **overall interpretation** confidence (a monotonic combination — the pipeline is never more confident than its weakest necessary stage). Low overall confidence downgrades language ("possible", "cannot reliably assess") and can block comparison claims.

## 6. Explanation system

Every major conclusion carries an `Explanation { observation, reasoning, confidence, evidence[], limitations[] }`. The UI's **"Why?"** button reveals reasoning + limitations; **"Evidence"** reveals the cited sources. No claim renders without these fields populated.

## 7. Longitudinal integrity

Photos captured weeks/months apart are aligned to a **standardized pose/scale/illumination-normalized** frame before any comparison. Comparisons always state lighting/quality limitations and never assert that an image *proves* treatment efficacy — only that *apparent* change was observed, with confidence.

## 8. Security & privacy (summary)

AuthN (JWT access + rotating refresh), RBAC (`user`, `clinician`, `admin`), encrypted storage, per-user data export & hard delete, explicit consent management, append-only audit log, minimal metadata, **no facial recognition / no identity matching**, **images are never sold or used for ads**. Full detail in [`07-safety-architecture.md`](07-safety-architecture.md) and the security section of the root README.

## 9. Fairness by design

Evaluation is **stratified**, never aggregate-only: Fitzpatrick I–VI, age band, sex, device manufacturer, lighting condition, geography. See [`08-roadmap.md`](08-roadmap.md) §Dataset & Evaluation.

## 10. Deployment topology

```
[Browser] ─https─ [Next.js/Vercel or Node] ─https─ [FastAPI (uvicorn/gunicorn)]
                                                     ├── PostgreSQL + pgvector
                                                     ├── S3-compatible bucket
                                                     ├── CV worker(s) (same image, GPU optional)
                                                     └── LLM provider (network egress allowlisted)
```

CV inference runs either in-process (MVP) or as a separate worker pool (production) — the service interface is identical, so scaling out is a deployment change, not a code change.
