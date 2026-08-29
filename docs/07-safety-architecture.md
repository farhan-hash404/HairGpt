# HairGPT — Safety Architecture

The safety layer is **deterministic** and sits *above* the LLM. It can hard-override any downstream output. It runs on structured observations (never on the LLM's free text), so it cannot be talked out of a referral by prompt content.

## Verdict model
`verdict ∈ { ok, caution, refer }`
- **ok** — routine wellness guidance permitted.
- **caution** — guidance permitted but language downgraded; monitoring + clinician-discussion points emphasized.
- **refer** — **cosmetic/self-treatment recommendations are suppressed entirely**; output becomes a professional-evaluation referral only.

## Red-flag rules (`backend/app/safety/rules.py`)
Pure functions over observations. Any single high-severity flag forces `refer`.

**Skin (SkinGPT) — force `refer`:**
- suspicious lesion features (e.g. asymmetry/border/color/diameter/evolution signals in observations)
- rapidly changing / evolving lesion (longitudinal delta above threshold)
- severe inflammation / infection-like appearance (redness + swelling + exudate signals)
- facial swelling / suspected severe allergic reaction
- signs consistent with a severe/urgent presentation

**Hair (HairGPT) — force `refer`:**
- scarring-alopecia-like signals (scalp scarring/loss of follicular openings appearance)
- pustules/boggy scalp/infection-like appearance
- sudden patchy loss appearance (possible alopecia areata) → clinician
- painful/rapidly spreading scalp changes

**Cross-cutting caution triggers:** low overall confidence, poor image quality that still passed, conflicting observations, minors, or user-reported systemic symptoms.

Each rule returns `{code, severity, matched, rationale}` and is recorded in `safety_verdicts.triggered_rules` for audit.

## Override mechanics (`backend/app/safety/engine.py`)
```
observations ─► run all rules ─► collect flags
   high-severity flag?  ─► verdict = refer
                          ─► recommendation set = [ referral ] only (cosmetic suppressed)
                          ─► LLM prompt = REFERRAL_TEMPLATE (no cosmetic content injected)
   medium flag / low conf ─► verdict = caution (downgrade language)
   else ─► verdict = ok
```
The engine returns a `SafetyVerdict` that the orchestrator applies **before** the recommendation engine and LLM run. The LLM never sees suppressed content, so it cannot reintroduce it.

## Prescription prohibition (structural, not prompt-based)
- The Recommendation Engine has **no prescription code path**; `is_prescription` is fixed `false` and enforced by a DB `CHECK` constraint.
- Prescription-only drugs are on a blocklist: they may appear **only** as *clinician-discussion points* ("ask your clinician whether X is appropriate"), never as an instruction to take them, and never with a dose the app invented.
- The LLM system prompt forbids prescribing, dosing prescription drugs, or claiming diagnosis; but the guarantee does **not** rely on the prompt — it is enforced by the engine and schema.

## Language & claim discipline
The LLM is constrained to distinguish, in wording:
- **visual observation** ("the image appears to show…")
- **AI inference** ("this may be consistent with…")
- **medical evidence** (cited)
- **clinician diagnosis** (only a professional can make one)

Banned outputs (post-filtered): definitive diagnoses, efficacy proofs from images, invented measurements, prescription/dosing directives. A regex+rule post-filter scrubs residual violations and, if it must strip content, lowers confidence and appends a limitation.

## Consent & data-safety gates
- Analysis endpoints hard-require current `storage`+`analysis` consent.
- **No facial recognition / identity matching** anywhere; face landmarks are used only for alignment/cropping and are not persisted as biometric templates.
- Images are encrypted at rest; **never sold, never used for advertising**; export & hard-delete are first-class.
- Audit log is append-only with hashed, minimal metadata (no raw IPs, no biometric identifiers).

## Failure-safe defaults
If any stage errors or confidence is unknown, the system defaults to the **more cautious** path (at least `caution`, degrade language, recommend professional input) rather than emitting confident guidance.
