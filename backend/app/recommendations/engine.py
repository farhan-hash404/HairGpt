from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.cv.types import Observation
from app.rag.retriever import EvidenceRef, retrieve
from app.safety.engine import SafetyVerdict

# Prescription-only agents. These may ONLY ever appear as clinician-discussion
# points ("ask your clinician whether X is appropriate") — NEVER as an app
# instruction to take them, and NEVER with an app-invented dose.
PRESCRIPTION_BLOCKLIST = {
    "finasteride",
    "dutasteride",
    "oral minoxidil",
    "spironolactone",
    "tretinoin",
    "isotretinoin",
    "topical corticosteroid (prescription)",
    "antibiotics",
}


@dataclass
class RecommendationOut:
    type: str  # care_guidance | clinician_discussion_point | product | ingredient | routine_step | referral
    title: str
    body: str
    confidence: float
    requires_clinician: bool = False
    is_prescription: bool = False  # ALWAYS False by construction
    evidence: list[EvidenceRef] = field(default_factory=list)


def _concern_query(domain: str, observations: list[Observation]) -> str:
    kinds = {o.kind: o for o in observations}
    terms: list[str] = [domain]
    if domain == "hair":
        sv = kinds.get("scalp_visibility")
        dens = kinds.get("apparent_density")
        if sv and (sv.value_num or 0) > 0.3:
            terms += ["increased scalp visibility", "thinning", "hair care"]
        if dens and dens.value_label and "sparse" in (dens.value_label or ""):
            terms += ["patterned hair loss", "androgenetic alopecia", "gentle scalp care"]
        terms += ["seborrheic dermatitis", "dandruff", "scalp health"]
    else:
        if (kinds.get("redness").value_num if kinds.get("redness") else 0) or 0 > 0.2:
            terms += ["redness", "sensitive skin", "moisturizer"]
        if (kinds.get("acne_like_lesion_count").value_num if kinds.get("acne_like_lesion_count") else 0) or 0 > 5:
            terms += ["acne", "cleanser"]
        terms += ["sunscreen", "skin barrier", "patch testing"]
    return " ".join(terms)


def build_recommendations(
    db: Session,
    domain: str,
    observations: list[Observation],
    safety: SafetyVerdict,
    overall_confidence: float,
) -> list[RecommendationOut]:
    """Produce evidence-gated recommendations.

    - If safety verdict is 'refer', cosmetic/self-treatment recs are SUPPRESSED and
      only a referral is returned.
    - Every care-guidance recommendation must attach >=1 evidence ref or it is dropped.
    - Prescription drugs never appear as instructions — only clinician-discussion points.
    """
    if safety.verdict == "refer":
        return [
            RecommendationOut(
                type="referral",
                title="Please seek professional evaluation",
                body=safety.message,
                confidence=0.95,
                requires_clinician=True,
            )
        ]

    evidence = retrieve(db, _concern_query(domain, observations), domain)
    recs: list[RecommendationOut] = []

    # 1) Evidence-backed general care guidance.
    care_evidence = [e for e in evidence if e.evidence_grade in ("systematic_review", "guideline", "regulatory_label", "expert_review")]
    if care_evidence:
        top = care_evidence[:2]
        recs.append(
            RecommendationOut(
                type="care_guidance",
                title="Evidence-based self-care to consider",
                body=(
                    "General, non-prescription steps supported by the cited sources. These are "
                    "supportive measures, not a diagnosis or a cure."
                ),
                confidence=round(min(0.8, overall_confidence + 0.1), 2),
                evidence=top,
            )
        )

    # 2) Ingredient guidance (OTC only), evidence-gated.
    for e in evidence:
        low = e.text.lower()
        if domain == "hair" and "ketoconazole" in low:
            recs.append(_ingredient_rec("Consider an antifungal medicated shampoo", "OTC ketoconazole or zinc pyrithione shampoos, used as directed, may help a flaky/itchy scalp.", overall_confidence, [e]))
        if domain == "skin" and "sunscreen" in low:
            recs.append(_ingredient_rec("Daily broad-spectrum sunscreen", "Apply broad-spectrum SPF 30+ daily as a foundational step.", overall_confidence, [e]))
        if domain == "skin" and "moisturizer" in low:
            recs.append(_ingredient_rec("Fragrance-free moisturizer", "A humectant + emollient moisturizer supports the skin barrier; fragrance-free suits reactive skin.", overall_confidence, [e]))

    # 3) Clinician-discussion points (prescription options mentioned, never prescribed).
    if domain == "hair":
        recs.append(
            RecommendationOut(
                type="clinician_discussion_point",
                title="Discuss patterned hair loss options with a clinician",
                body=(
                    "If thinning is bothersome, a clinician can assess whether prescription options "
                    "(which this app does not prescribe or dose) are appropriate for you, alongside OTC measures."
                ),
                confidence=0.6,
                requires_clinician=True,
                evidence=[e for e in evidence if e.source in ("NICE", "AAD")][:1],
            )
        )
    if domain == "skin":
        recs.append(
            RecommendationOut(
                type="clinician_discussion_point",
                title="When to see a clinician for skin concerns",
                body=(
                    "Persistent, painful, scarring, or changing skin concerns should be reviewed in person. "
                    "A clinician can discuss prescription treatments where appropriate — this app never prescribes."
                ),
                confidence=0.6,
                requires_clinician=True,
                evidence=[e for e in evidence if e.source in ("NHS", "AAD")][:1],
            )
        )

    # Caution downgrade: reduce confidence and add a monitoring note.
    if safety.verdict == "caution":
        for r in recs:
            r.confidence = round(r.confidence * 0.8, 2)
        recs.append(
            RecommendationOut(
                type="care_guidance",
                title="Monitor and re-scan",
                body="Findings were borderline. Re-scan in good lighting in a few weeks and consider a clinician's input.",
                confidence=0.55,
            )
        )

    # Drop any care/ingredient rec that ended up without evidence (grounding contract).
    grounded = [
        r
        for r in recs
        if r.type in ("clinician_discussion_point", "referral") or r.evidence
    ]
    # Final safety net: assert no prescription ever slips through.
    for r in grounded:
        assert r.is_prescription is False
        if any(drug in r.body.lower() for drug in PRESCRIPTION_BLOCKLIST) and r.type not in (
            "clinician_discussion_point",
            "referral",
        ):
            r.type = "clinician_discussion_point"
            r.requires_clinician = True
    return grounded


def _ingredient_rec(title, body, conf, evidence):
    return RecommendationOut(
        type="ingredient",
        title=title,
        body=body,
        confidence=round(min(0.75, conf + 0.05), 2),
        evidence=evidence,
    )
