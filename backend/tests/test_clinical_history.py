"""Clinical history: the context photos cannot show.

The costliest failure this product can make is letting someone spend months on
cosmetic routines while a reversible cause (thyroid, iron, a drug side effect,
telogen effluvium) goes undiagnosed. These tests lock in that history actually
reaches the safety engine and changes the outcome.
"""
from __future__ import annotations

import pytest

from app.cv.types import ConfidenceScore, Observation
from app.safety.engine import evaluate
from app.schemas.history import flag_medications
from tests.conftest import authenticate, complete_scan, grant_consent


def _obs(kind="scalp_visibility", num=0.35, conf=0.8):
    return Observation(kind=kind, value_num=num, confidence=ConfidenceScore(conf, "t", "t"))


BASELINE = {"overall_confidence": 0.8, "min_quality_confidence": 0.8}


# --- rules fire ------------------------------------------------------------

def test_clean_history_stays_ok():
    assert evaluate("hair", [_obs()], BASELINE).verdict == "ok"


@pytest.mark.parametrize(
    "condition",
    ["thyroid_condition", "iron_deficiency", "autoimmune_condition", "pcos"],
)
def test_treatable_systemic_cause_raises_caution(condition):
    verdict = evaluate("hair", [_obs()], {**BASELINE, condition: True})
    assert verdict.verdict == "caution"
    assert "history_possible_systemic_cause" in verdict.red_flags


def test_telogen_effluvium_pattern_is_recognised():
    """Trigger + diffuse/sudden onset is managed differently from patterned loss."""
    verdict = evaluate("hair", [_obs()], {**BASELINE, "postpartum": True, "pattern": "diffuse"})
    assert verdict.verdict == "caution"
    assert "history_possible_telogen_effluvium" in verdict.red_flags


def test_trigger_without_diffuse_pattern_does_not_fire():
    """A trigger alone is not enough — the rule needs the matching presentation."""
    verdict = evaluate("hair", [_obs()], {**BASELINE, "major_stress": True, "pattern": "receding"})
    assert "history_possible_telogen_effluvium" not in verdict.red_flags


def test_painful_scalp_with_scalp_condition_forces_referral():
    """Scarring loss is permanent; the window to act is while photos look normal."""
    verdict = evaluate("hair", [_obs()], {**BASELINE, "scalp_pain": True, "scalp_condition": True})
    assert verdict.verdict == "refer"
    assert verdict.suppressed_cosmetic is True


def test_medication_association_raises_caution():
    verdict = evaluate("hair", [_obs()], {**BASELINE, "medication_associated_shedding": True})
    assert verdict.verdict == "caution"
    assert "history_medication_associated_shedding" in verdict.red_flags


def test_traction_risk_needs_both_signals():
    with_both = evaluate("hair", [_obs()], {**BASELINE, "tight_hairstyles": True, "pattern": "receding"})
    styling_only = evaluate("hair", [_obs()], {**BASELINE, "tight_hairstyles": True, "pattern": "crown"})
    assert "history_traction_risk" in with_both.red_flags
    assert "history_traction_risk" not in styling_only.red_flags


def test_history_rules_do_not_apply_to_skin_scans():
    verdict = evaluate("skin", [_obs("redness", 0.1)], {**BASELINE, "thyroid_condition": True})
    assert "history_possible_systemic_cause" not in verdict.red_flags


# --- medication flagging ---------------------------------------------------

def test_flags_known_shedding_associated_medications():
    flagged = flag_medications(["Warfarin 5mg", "Vitamin D", "lithium carbonate"])
    assert len(flagged) == 2
    assert "Vitamin D" not in flagged


def test_does_not_flag_unrelated_medications():
    assert flag_medications(["paracetamol", "vitamin c", "cetirizine"]) == []


# --- end to end ------------------------------------------------------------

def test_history_reaches_the_analysis(client):
    """Saved history must change a later scan's verdict with no extra input."""
    headers = authenticate(client, "history@example.com")
    grant_consent(client, headers)

    client.put(
        "/api/v1/history",
        json={"thyroid_condition": True, "pattern": "diffuse", "onset": "sudden", "recent_illness": True},
        headers=headers,
    )
    sid = complete_scan(client, headers, "hair")
    result = client.get(f"/api/v1/scans/{sid}/result", headers=headers).json()

    flags = result["safety_verdict"]["red_flags"]
    assert "history_possible_systemic_cause" in flags
    assert "history_possible_telogen_effluvium" in flags


def test_history_appears_in_the_doctor_report(client):
    headers = authenticate(client, "report@example.com")
    grant_consent(client, headers)
    client.put(
        "/api/v1/history",
        json={"pattern": "crown", "family_history_hair_loss": True, "medications": ["warfarin"]},
        headers=headers,
    )
    sid = complete_scan(client, headers, "hair")
    report = client.get(f"/api/v1/scans/{sid}/doctor-report", headers=headers).json()

    history = report["clinical_history"]
    assert history is not None
    assert history["pattern"] == "crown"
    assert history["family_history_hair_loss"] is True
    assert history["medications_associated_with_shedding"] == ["warfarin"]


def test_analysis_works_with_no_history_recorded(client):
    """History is optional; its absence must not break anything."""
    headers = authenticate(client, "nohistory@example.com")
    grant_consent(client, headers)
    assert client.get("/api/v1/history", headers=headers).json() is None
    sid = complete_scan(client, headers, "hair")
    assert client.get(f"/api/v1/scans/{sid}/result", headers=headers).status_code == 200
