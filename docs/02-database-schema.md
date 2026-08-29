# HairGPT — Database Schema

PostgreSQL 15+ with the `vector` (pgvector) and `pgcrypto` extensions. All timestamps are `timestamptz` (UTC). All primary keys are UUID v4. Soft-delete via `deleted_at`; hard-delete honored by the erasure job.

## Entity overview

```
users ──1:n── consents
  │  └─1:n── audit_logs
  │  └─1:n── scan_sessions ──1:n── scan_images ──1:1── image_quality_reports
  │                │                     └─1:n── observations ──1:n── observation_evidence ─┐
  │                └─1:1── analyses ──1:1── safety_verdicts                                  │
  │                                  └─1:n── recommendations                                 │
  │  └─1:n── treatments ──1:n── adherence_logs                                              │
  │  └─1:n── products ──1:n── product_ingredients                                           │
  └─1:n── comparisons                                                                        │
evidence_documents ──1:n── evidence_chunks (vector) ◄───────────────────────────────────────┘
```

## Tables

### `users`
| col | type | notes |
|---|---|---|
| id | uuid pk | |
| email | citext unique | |
| password_hash | text | argon2id |
| role | text | `user`\|`clinician`\|`admin` |
| display_name | text | |
| fitzpatrick_self | smallint null | self-reported I–VI, for fairness stratification only |
| year_of_birth | smallint null | age band, not exact DOB |
| sex | text null | self-reported |
| is_active | bool | |
| created_at / updated_at / deleted_at | timestamptz | |

### `consents`
Explicit, versioned, per-purpose. `purpose ∈ {storage, analysis, longitudinal, clinician_share, research_optin}`. `granted bool`, `policy_version text`, `granted_at`, `revoked_at`. Analysis is blocked unless `storage`+`analysis` are currently granted. `research_optin` defaults false and is never required.

### `scan_sessions`
| col | type | notes |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| domain | text | `hair`\|`skin` |
| status | text | `capturing`\|`quality_review`\|`analyzing`\|`complete`\|`rejected` |
| capture_protocol | text | e.g. `hair_v1` (7 views) / `skin_v1` (3 views) |
| device_make | text null | fairness metadata (make only, not identifiers) |
| lighting_label | text null | `daylight`\|`indoor_warm`\|`indoor_cool`\|`mixed`\|`low` |
| created_at / completed_at | timestamptz | |

### `scan_images`
| col | type | notes |
|---|---|---|
| id | uuid pk | |
| session_id | uuid fk | |
| view | text | hair: `front_hairline\|left_temple\|right_temple\|top\|crown\|sides\|back`; skin: `front\|left\|right` |
| storage_key | text | object-storage key (encrypted object) |
| width / height | int | |
| captured_at | timestamptz | |
| quality_passed | bool null | set by quality gate |
| alignment_json | jsonb null | pose/scale normalization transform for longitudinal compare |

### `image_quality_reports`
1:1 with `scan_images`. Columns: `blur_score`, `exposure_score`, `overexposed_frac`, `distance_ok bool`, `angle_ok bool`, `scalp_visibility` (hair only), `overall_pass bool`, `reasons text[]`, `confidence numeric`. Images with `overall_pass=false` are **not analyzed**.

### `observations`
Typed CV outputs. One row per measured/observed attribute.
| col | type | notes |
|---|---|---|
| id | uuid pk | |
| session_id | uuid fk | |
| image_id | uuid fk null | null for session-level aggregates |
| kind | text | e.g. `hairline_position`, `crown_density`, `scalp_visibility`, `skin_oiliness`, `redness`, `pigmentation`, `acne_like_lesion_count`, `pore_visibility`, `texture`, `fine_lines`, `under_eye` |
| value_num | numeric null | quantitative value |
| value_label | text null | qualitative label |
| unit | text null | |
| confidence | numeric | 0..1 |
| confidence_basis | text | how confidence was derived |
| model_name / model_version | text | provenance |
| is_mock | bool | **true when produced by non-validated mock inference** |
| observation_type | text | `visual_observation`\|`ai_inference` (never `diagnosis`) |
| created_at | timestamptz | |

### `analyses`
1:1 per completed session. Holds the assembled interpretation.
`session_id`, `skin_appearance_index numeric null` (skin), `hair_summary jsonb null`, `overall_confidence numeric`, `llm_model text`, `llm_version text`, `explanation jsonb` (observation/reasoning/confidence/evidence/limitations), `status text`.

### `safety_verdicts`
1:1 per analysis. `verdict text ∈ {ok, caution, refer}`, `red_flags text[]`, `triggered_rules jsonb`, `suppressed_cosmetic bool`, `message text`, `created_at`. When `verdict='refer'`, recommendations of type cosmetic/self-treatment are withheld.

### `recommendations`
`analysis_id`, `type text ∈ {care_guidance, clinician_discussion_point, product, ingredient, routine_step, referral}`, `title`, `body`, `evidence_refs uuid[]` (→ evidence_documents), `confidence numeric`, `requires_clinician bool`, `is_prescription bool` (**always false by construction; a check constraint enforces it**), `created_at`.

> **Constraint:** `CHECK (is_prescription = false)` on `recommendations` — the system is structurally incapable of storing an autonomous prescription.

### `treatments`
User-entered regimen. `user_id`, `category text ∈ {oral_med, topical, procedure, shampoo, scalp_care, other}`, `name`, `dose text null`, `frequency text null`, `start_date date`, `end_date date null`, `notes`, `is_prescribed_by_clinician bool` (user attests a clinician prescribed it — the app never prescribes), `created_at`.

### `adherence_logs`
`treatment_id`, `date date`, `taken bool`, `note text null`. Adherence % = taken / expected over window.

### `products` / `product_ingredients`
`products`: `user_id`, `name`, `manufacturer`, `barcode text null`, `expiry text null`, `batch text null`, `source text ∈ {scan_ocr, manual}`, `raw_ocr text null`, `confidence numeric`.
`product_ingredients`: `product_id`, `name`, `is_active bool`, `concentration text null`, `is_potential_irritant bool`, `duplicate_of uuid null`, `evidence_refs uuid[]`.

### `comparisons`
`user_id`, `session_before uuid`, `session_after uuid`, `metrics jsonb` (per-metric delta + confidence), `alignment_quality numeric`, `limitations text[]`, `created_at`. No comparison asserts efficacy; deltas are "apparent change".

### `evidence_documents`
Curated medical sources. `source text ∈ {AAD, FDA, NICE, NHS, peer_reviewed, systematic_review, guideline}`, `title`, `url`, `publisher`, `pub_date date null`, `evidence_grade text`, `retrieved_at`. Social media is **not** an allowed source (enforced by a source enum + ingestion allowlist).

### `evidence_chunks`
`document_id`, `chunk_index int`, `text`, `embedding vector(768)`, `token_count int`. HNSW/IVF index on `embedding`. RAG retrieves here; every recommendation's `evidence_refs` resolves to the parent documents.

### `audit_logs`
Append-only. `user_id null`, `actor_id`, `action text`, `resource_type`, `resource_id`, `ip_hash text` (hashed, minimal metadata), `meta jsonb`, `created_at`. No raw IPs, no biometric identifiers.

## Indexing highlights
- `scan_sessions(user_id, created_at desc)` — timeline queries.
- `observations(session_id, kind)` — assembly.
- `evidence_chunks` vector index (cosine).
- `adherence_logs(treatment_id, date)` unique — one log per day.

Migrations are managed by **Alembic** (see README → migrations).
