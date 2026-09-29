"""The deterministic hallucination gate."""
from __future__ import annotations

from app.agents.citations import audit, policy_violations

SOURCES = {
    1: "It's normal to lose hair. We can lose between 50 and 100 hairs a day, often without noticing.",
    2: "Finasteride and minoxidil are the main treatments for male pattern baldness. "
       "Minoxidil can also be used to treat female pattern baldness.",
}


def test_faithful_cited_answer_passes():
    report = audit("Losing 50 to 100 hairs a day is normal [1]. Minoxidil can be used for female pattern "
                   "baldness [2]. A GP can advise what suits you.", SOURCES)
    assert report.passed, report.to_dict()
    assert report.support_ratio == 1.0


def test_fabricated_citation_fails():
    report = audit("Losing 50 to 100 hairs a day is normal [7].", SOURCES)
    assert not report.passed and report.fabricated_citations == [7]


def test_fabricated_statistic_fails():
    report = audit("We can lose between 200 and 300 hairs a day without noticing [1].", SOURCES)
    assert not report.passed
    assert "200" in report.unmatched_numbers and "300" in report.unmatched_numbers


def test_invented_treatment_fails():
    report = audit("Finasteride, minoxidil and dutasteride are the main treatments for male pattern baldness [2].",
                   SOURCES)
    assert not report.passed and report.unmatched_terms == ["dutasteride"]


def test_uncited_medical_claim_fails():
    report = audit("Stress causes most hair loss in young men.", SOURCES)
    assert not report.passed and report.uncited_claims


def test_unsupported_sentence_fails():
    report = audit("Wearing hats usually causes baldness in older adults [1].", SOURCES)
    assert not report.passed and report.unsupported


def test_advice_to_see_a_clinician_needs_no_citation():
    assert audit("A GP or pharmacist can advise whether treatment is right for you.", SOURCES).passed


def test_policy_violations_are_detected():
    assert "dosing" in policy_violations("Take 1 mg of finasteride daily.")
    assert "dosing" in policy_violations("Finasteride 1 mg/day is licensed for men.")
    assert "diagnosis" in policy_violations("You have androgenetic alopecia.")
    assert "prescription_directive" in policy_violations("You should take finasteride to stop the loss.")
    # Informational statements about medicines are not directives or doses.
    assert policy_violations("Finasteride is available on prescription only.") == []
    assert policy_violations("Minoxidil 5% w/w (without propellant)") == []


def test_feedback_names_the_specific_problems():
    report = audit("We can lose 400 hairs a day [9]. Stress causes baldness.", SOURCES)
    feedback = report.feedback()
    assert "9" in feedback and "400" in feedback and "no citation" in feedback
