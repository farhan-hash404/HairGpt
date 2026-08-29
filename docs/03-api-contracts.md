# HairGPT — API Contracts

Base URL: `/api/v1`. Auth: `Authorization: Bearer <access_jwt>`. All bodies JSON unless noted. Errors follow `{ "error": { "code", "message", "details?" } }`. Every response that contains an AI conclusion also contains an `explanation` object.

## Conventions
- `ConfidenceScore = { value: number(0..1), basis: string, method: string }`
- `Explanation = { observation: string, reasoning: string, confidence: ConfidenceScore, evidence: EvidenceRef[], limitations: string[] }`
- `EvidenceRef = { id, source, title, url, publisher, evidence_grade }`
- `observation_type ∈ {"visual_observation","ai_inference"}` — never `"diagnosis"`.

## Auth
| Method | Path | Body → Response |
|---|---|---|
| POST | `/auth/register` | `{email,password,display_name}` → `{user}` (+ consent prompt required next) |
| POST | `/auth/login` | `{email,password}` → `{access_token, refresh_token, user}` |
| POST | `/auth/refresh` | `{refresh_token}` → `{access_token, refresh_token}` |
| POST | `/auth/logout` | `{refresh_token}` → `204` (revokes refresh) |
| GET | `/auth/me` | → `{user, consents[]}` |

## Consent (required before any analysis)
| Method | Path | |
|---|---|---|
| GET | `/consents` | current consent state + policy_version |
| POST | `/consents` | `{purpose, granted, policy_version}` → updated consent. Analysis endpoints return `403 consent_required` if `storage`+`analysis` not granted. |

## Scans
| Method | Path | Description |
|---|---|---|
| POST | `/scans` | `{domain:"hair"|"skin", capture_protocol, device_make?, lighting_label?}` → `{session_id, required_views[], status:"capturing"}` |
| POST | `/scans/{id}/images/presign` | `{view, content_type}` → `{upload_url, storage_key}` (client PUTs the image directly to storage) |
| POST | `/scans/{id}/images` | `{view, storage_key, width, height}` → runs **quality gate synchronously** → `{image_id, quality: ImageQualityReport}`. If `overall_pass=false`, response includes `retake_guidance[]` and the image is not queued for analysis. |
| POST | `/scans/{id}/analyze` | begins analysis once all required views pass quality → `{status:"complete"}` (or `409` if views missing/failed). Optional body carries a **self-reported symptom check** (see below) that feeds the safety engine. |
| GET | `/scans/{id}` | → session + images + quality reports |
| GET | `/scans/{id}/result` | → `Analysis` (observations, safety_verdict, recommendations, explanation, overall confidence). `202` while analyzing. |
| GET | `/scans` | list sessions (timeline source), paginated |

### `ImageQualityReport`
```json
{ "overall_pass": false,
  "blur_score": 0.31, "exposure_score": 0.72, "overexposed_frac": 0.02,
  "distance_ok": true, "angle_ok": false, "scalp_visibility": 0.18,
  "reasons": ["angle_off","low_scalp_visibility"],
  "retake_guidance": ["Tilt the camera slightly downward","Part the hair to expose the scalp"],
  "confidence": {"value":0.83,"basis":"laplacian+exposure heuristics","method":"quality_gate_v1"} }
```

### Symptom check (optional body on `/scans/{id}/analyze`)
Several high-severity red flags cannot be detected from images by the current CV stack. Rather than let the safety net silently do nothing, the client asks the user directly and submits the answers here. **A single `true` is enough on its own to force `verdict:"refer"`** and suppress all cosmetic guidance — self-report is treated as safety-relevant evidence, never as a diagnosis.

```json
{ "hair_symptoms": { "pustules": false, "boggy_scalp": false, "scarring_signal": false,
                     "sudden_patchy_loss": false, "systemic_symptoms": false },
  "skin_symptoms": { "lesion_abcde_signal": 0.0, "lesion_change_delta": 0.0,
                     "facial_swelling": false, "allergic_reaction": false,
                     "infection_like": false, "systemic_symptoms": false },
  "is_minor": false }
```
The body is optional; omitting it analyzes with no reported symptoms.

### `Analysis` (hair example, abbreviated)
```json
{ "session_id":"...", "domain":"hair", "status":"complete",
  "overall_confidence": {"value":0.61,"basis":"min of stage confidences","method":"agg_v1"},
  "observations":[
    {"kind":"scalp_visibility","value_num":0.22,"unit":"fraction","observation_type":"visual_observation",
     "confidence":{"value":0.7,"basis":"segmentation area ratio","method":"seg_mock_v1"},
     "is_mock":true,"model":"mock-scalp-seg@0.1"},
    {"kind":"hairline_position","value_label":"apparent recession at temples","observation_type":"ai_inference",
     "confidence":{"value":0.55,"basis":"landmark heuristic","method":"hairline_mock_v1"},"is_mock":true}
  ],
  "safety_verdict":{"verdict":"caution","red_flags":[],"message":"..."},
  "recommendations":[
    {"type":"care_guidance","title":"Gentle scalp care","body":"...","confidence":{...},
     "requires_clinician":false,"is_prescription":false,"evidence":[EvidenceRef,...]},
    {"type":"clinician_discussion_point","title":"Discuss patterned hair loss options","body":"...","requires_clinician":true}
  ],
  "explanation": Explanation,
  "disclaimers":["Image-based observations, not a diagnosis.","Mock inference — not medically validated."] }
```

## Comparison
| Method | Path | |
|---|---|---|
| POST | `/comparisons` | `{session_before, session_after}` → aligns, computes per-metric apparent deltas |
| GET | `/comparisons/{id}` | → `{ before, after, aligned_overlay_url, diff_url, metrics:[{kind,before,after,delta,confidence}], alignment_quality, limitations[], explanation }` |

Response always includes `limitations` describing lighting/quality caveats and a fixed disclaimer that images do not prove efficacy.

## Treatments
| Method | Path | |
|---|---|---|
| GET/POST | `/treatments` | list / create `{category,name,dose?,frequency?,start_date,end_date?,notes?,is_prescribed_by_clinician?}` |
| PATCH/DELETE | `/treatments/{id}` | update / remove |
| POST | `/treatments/{id}/adherence` | `{date, taken, note?}` |
| GET | `/treatments/adherence/summary` | `{window_days}` → per-treatment & overall adherence % |

> The API has **no endpoint** that prescribes medication. `POST /treatments` records what a user (or their clinician) is already doing; it never generates a prescription.

## Timeline
| GET | `/timeline` | → merged series: hairline, crown, scalp_visibility, apparent_density, treatment events, adherence, scan history — each point tagged with confidence and `is_mock`. |

## Products (product intelligence)
| Method | Path | |
|---|---|---|
| POST | `/products/scan` | `{image_storage_key}` → OCR extract → `{name,manufacturer,expiry?,batch?,ingredients:[{name,is_active,concentration?,is_potential_irritant,duplicate_of?}], confidence}` |
| GET/POST | `/products` | list / save |
| POST | `/products/recommend` | `{goals[], budget?, regimen_product_ids[]}` → evidence-gated, ingredient-compatibility-checked recommendations. **Ranking never uses affiliate revenue** (there is no affiliate field). |

## SkinGPT
Same scan endpoints with `domain:"skin"`, `capture_protocol:"skin_v1"`, views `front|left|right`. `Analysis` adds `skin_appearance_index`, `primary_concern`, `secondary_concern`, `routine:{morning[],night[]}`, `ingredient_conflicts[]`.

## Reports
| GET | `/scans/{id}/doctor-report` | → structured clinician-facing draft (PDF/JSON): observations, confidences, is_mock flags, safety verdict, treatment history, explicit "not a diagnosis" framing, evidence citations. |

## Data rights
| Method | Path | |
|---|---|---|
| POST | `/account/export` | enqueue full export (JSON + images) → download link |
| DELETE | `/account` | hard-delete: purges images from storage, rows, and vectors; writes final audit entry |

## Explainability endpoints
| GET | `/analyses/{id}/why` | reasoning + limitations for each conclusion |
| GET | `/analyses/{id}/evidence` | resolved EvidenceRef[] with source grading |

All endpoints are rate-limited and audit-logged. OpenAPI is auto-generated at `/docs` (Swagger) and `/openapi.json`.
