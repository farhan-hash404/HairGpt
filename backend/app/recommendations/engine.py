"""Evidence-gated recommendations, expressed as declarative rules.

Each rule has a trigger (observations, safety verdict, reported history), a
retrieval query phrased the way the sources phrase it, and plain-language text.
A rule fires only if retrieval finds evidence that passes the abstention test;
otherwise it is dropped — the grounding contract.

The factual statements in the rule bodies were checked against the retrieved
passages when the rules were written (see tests/test_recommendations_grounded.py),
and every recommendation carries the passages themselves, so a reader can
verify each one.

Two guarantees are structural rather than prompted:
  * a "refer" safety verdict returns ONLY a referral — no care advice at all;
  * nothing is ever a prescription (is_prescription is fixed False, and a
    database CHECK constraint enforces it).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from app.cv.types import Observation
from app.rag.index import get_rag_index
from app.rag.retriever import EvidenceRef, _to_ref, default_reranker, is_supported
from app.safety.engine import SafetyVerdict

log = logging.getLogger("hairgpt.recommendations")

# Prescription-only agents. They may ONLY ever appear inside clinician-discussion
# points ("ask whether X is appropriate") — never as an instruction, never dosed.
PRESCRIPTION_BLOCKLIST = {
    "finasteride",
    "dutasteride",
    "oral minoxidil",
    "spironolactone",
    "tretinoin",
    "isotretinoin",
    "baricitinib",
    "ritlecitinib",
    "topical corticosteroid (prescription)",
    "antibiotics",
}

# Types that are advice about seeing someone or using the app, not medical care
# claims, and so need no citation.
EVIDENCE_EXEMPT = {"referral", "monitoring"}


@dataclass
class RecommendationOut:
    type: str  # care_guidance | clinician_discussion_point | referral | monitoring | ingredient | ...
    title: str
    body: str
    confidence: float
    requires_clinician: bool = False
    is_prescription: bool = False  # ALWAYS False by construction
    evidence: list[EvidenceRef] = field(default_factory=list)
    rule_id: str = ""


@dataclass
class Context:
    domain: str
    observations: list[Observation]
    safety: SafetyVerdict
    overall_confidence: float
    signals: dict  # reported history + symptoms (the safety context)

    def obs(self, kind: str) -> Observation | None:
        return next((o for o in self.observations if o.kind == kind), None)

    @property
    def patterned_thinning(self) -> bool:
        density = self.obs("apparent_density") or self.obs("crown_density")
        scalp = self.obs("scalp_visibility")
        return bool(
            (density and density.value_label and "sparse" in density.value_label)
            or (scalp and (scalp.value_num or 0) >= 0.3)
            or self.signals.get("pattern") in ("receding", "crown")
        )

    @property
    def possible_effluvium(self) -> bool:
        trigger = any(self.signals.get(k) for k in (
            "recent_illness", "recent_surgery", "major_stress", "rapid_weight_loss", "postpartum"))
        return trigger and (self.signals.get("pattern") == "diffuse" or self.signals.get("onset") == "sudden")


@dataclass(frozen=True)
class Rule:
    id: str
    domain: str
    type: str
    title: str
    body: str
    query: str
    when: Callable[[Context], bool] = lambda ctx: True
    requires_clinician: bool = False
    base_confidence: float = 0.7


RULES: list[Rule] = [
    # --- Hair: always, unless referred -------------------------------------
    Rule(
        "normal-shedding", "hair", "care_guidance",
        "Some daily shedding is normal",
        "Losing some hair every day is normal and usually nothing to worry about. The cited sources "
        "give the typical daily range, which is useful context when judging your own shedding.",
        "It's normal to lose between 50 and 100 hairs a day",
    ),
    Rule(
        "see-gp", "hair", "clinician_discussion_point",
        "When to talk to a GP",
        "See a GP if you're worried about your hair loss. A GP can often tell what is causing it by "
        "looking at your hair, and can say which treatments are available.",
        "See a GP if you're worried about your hair loss; the GP may be able to tell what's causing it by looking at your hair",
        requires_clinician=True,
    ),
    # --- Hair: patterned thinning --------------------------------------------
    Rule(
        "patterned-options", "hair", "clinician_discussion_point",
        "Ask about treatments for patterned thinning",
        "Finasteride and minoxidil are the main treatments for patterned hair loss. Finasteride is "
        "prescription-only and not for women; minoxidil is available without a prescription. A pharmacist "
        "or GP can advise whether either suits you. HairGPT does not prescribe or dose medicines.",
        "Finasteride and minoxidil are the main treatments for male pattern baldness; minoxidil for female pattern",
        when=lambda ctx: ctx.patterned_thinning,
        requires_clinician=True,
    ),
    Rule(
        "minoxidil-stop-signs", "hair", "care_guidance",
        "If you use minoxidil, know when to stop",
        "The minoxidil label lists reasons to stop and ask a doctor: chest pain, a rapid heartbeat, "
        "faintness or dizziness; sudden unexplained weight gain; swollen hands or feet; scalp irritation "
        "or redness; unwanted facial hair; or no regrowth after four months.",
        "Stop use and ask a doctor if chest pain, rapid heartbeat, faintness or dizziness occurs",
        when=lambda ctx: ctx.patterned_thinning,
    ),
    # --- Hair: reported history ----------------------------------------------
    Rule(
        "flaky-scalp", "hair", "care_guidance",
        "An itchy, flaky scalp",
        "Dandruff is common and usually improves with an anti-dandruff shampoo. See a GP if things do "
        "not get better within a month.",
        "How to treat dandruff with anti-dandruff shampoo; see a GP if things do not get better in a month",
        when=lambda ctx: bool(ctx.signals.get("scalp_itch") or ctx.signals.get("scalp_condition")),
    ),
    Rule(
        "iron", "hair", "clinician_discussion_point",
        "Iron levels are worth checking",
        "Hair loss can be a symptom of iron deficiency anaemia. A GP can check for it with a blood test.",
        "iron deficiency anaemia symptoms hair loss coming out when brushing; the GP will usually do a blood test",
        when=lambda ctx: bool(ctx.signals.get("iron_deficiency")),
        requires_clinician=True,
    ),
    Rule(
        "thyroid", "hair", "clinician_discussion_point",
        "Mention your hair to whoever manages your thyroid",
        "An underactive thyroid can cause dry hair or hair loss, so it is worth raising at your next review.",
        "underactive thyroid symptoms include dry skin, dry hair or hair loss",
        when=lambda ctx: bool(ctx.signals.get("thyroid_condition")),
        requires_clinician=True,
    ),
    Rule(
        "pmos", "hair", "clinician_discussion_point",
        "A hormone condition can affect hair growth",
        "Polyendocrine metabolic ovarian syndrome (PMOS, formerly PCOS) can affect hair growth. A GP can "
        "advise on tests and treatment.",
        "Polyendocrine metabolic ovarian syndrome is a hormone condition that can affect hair growth",
        when=lambda ctx: bool(ctx.signals.get("pcos")),
        requires_clinician=True,
    ),
    Rule(
        "effluvium", "hair", "clinician_discussion_point",
        "Shedding after illness, stress or childbirth",
        "Diffuse shedding that begins a few months after a trigger such as illness, stress or childbirth "
        "can be telogen effluvium, a shedding phase that often resolves. A clinician can confirm the cause.",
        "telogen effluvium diffuse shedding months after childbirth illness or stress resolves",
        when=lambda ctx: ctx.possible_effluvium,
        requires_clinician=True,
    ),
    # --- Skin (domain implemented, not exposed) --------------------------------
    Rule(
        "sunscreen", "skin", "care_guidance",
        "Daily sun protection",
        "Use a sunscreen with at least SPF 30 and good UVA protection, and reapply as directed.",
        "What factor sunscreen should I use SPF 30 UVA protection",
    ),
    Rule(
        "acne-gp", "skin", "clinician_discussion_point",
        "When acne needs a GP",
        "See a GP if acne is not improving with pharmacy treatments or is causing scarring or distress.",
        "acne see a GP if pharmacy treatments have not worked",
        requires_clinician=True,
    ),
]


_evidence_cache: dict[tuple, tuple[EvidenceRef, ...]] = {}


def rule_evidence(db: Session, rule: Rule) -> list[EvidenceRef]:
    """Evidence for a rule, cached.

    Rule queries are fixed strings, so their evidence changes only when the
    corpus does: caching turns a ~1 s cross-encoder rerank into a lookup. The
    key uses the index's sync generation rather than the corpus fingerprint:
    two databases holding the same corpus (e.g. a test database) assign
    different document ids, and the fingerprint cannot tell them apart.
    """
    index = get_rag_index()
    if not index.ready:
        index.ensure(db)
    key = (id(index), index.generation, rule.query, rule.domain)
    if key not in _evidence_cache:
        if len(_evidence_cache) > 512:
            _evidence_cache.clear()
        chunks = index.search(rule.query, domain=rule.domain, k=2, per_doc=1, reranker=default_reranker())
        _evidence_cache[key] = tuple(_to_ref(c) for c in chunks if is_supported(c))
    return list(_evidence_cache[key])


def warm_cache(db: Session) -> int:
    """Pre-compute evidence for every rule (called at startup)."""
    return sum(1 for rule in RULES if rule_evidence(db, rule))


def build_recommendations(
    db: Session,
    domain: str,
    observations: list[Observation],
    safety: SafetyVerdict,
    overall_confidence: float,
    signals: dict | None = None,
) -> list[RecommendationOut]:
    if safety.verdict == "refer":
        return [
            RecommendationOut(
                type="referral",
                title="Please seek professional evaluation",
                body=safety.message,
                confidence=0.95,
                requires_clinician=True,
                rule_id="safety-referral",
            )
        ]

    ctx = Context(domain, observations, safety, overall_confidence, signals or {})
    recs: list[RecommendationOut] = []
    for rule in RULES:
        if rule.domain != domain or not rule.when(ctx):
            continue
        evidence = rule_evidence(db, rule)
        if not evidence and rule.type not in EVIDENCE_EXEMPT:
            log.info("rule %s dropped: no supporting evidence", rule.id)
            continue
        confidence = rule.base_confidence
        if rule.type == "care_guidance":
            # Care advice triggered by the images can be no surer than the images.
            confidence = min(confidence, max(0.3, overall_confidence + 0.2))
        recs.append(RecommendationOut(
            type=rule.type,
            title=rule.title,
            body=rule.body,
            confidence=round(confidence, 2),
            requires_clinician=rule.requires_clinician,
            evidence=evidence,
            rule_id=rule.id,
        ))

    if safety.verdict == "caution":
        for r in recs:
            r.confidence = round(r.confidence * 0.8, 2)
        recs.append(RecommendationOut(
            type="monitoring",
            title="Re-scan in a few weeks",
            body="Some findings were borderline. Re-scan in good, even lighting in a few weeks, and consider "
                 "a clinician's input sooner if anything changes quickly.",
            confidence=0.6,
            rule_id="caution-monitor",
        ))

    # Final safety net: no prescription can surface as an instruction.
    for r in recs:
        assert r.is_prescription is False
        if r.type not in ("clinician_discussion_point", "referral") and any(
            drug in r.body.lower() for drug in PRESCRIPTION_BLOCKLIST
        ):
            r.type = "clinician_discussion_point"
            r.requires_clinician = True
    return recs
