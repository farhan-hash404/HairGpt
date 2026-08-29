"""End-to-end API tests covering the clinical guarantees.

These are the invariants that must never regress:
  - analysis is blocked without consent
  - low-quality images are not analyzed
  - a red flag suppresses ALL cosmetic recommendations
  - no response ever contains a prescription
"""
from __future__ import annotations

import pytest

from app.cv.imageio import HAS_PIXELS
from tests.conftest import authenticate as _auth
from tests.conftest import grant_consent as _grant_consent
from tests.conftest import make_jpeg as _jpeg

pytestmark = pytest.mark.skipif(not HAS_PIXELS, reason="numpy/Pillow not installed")


def test_analysis_blocked_without_consent(client):
    h = _auth(client, "noconsent@example.com")
    r = client.post("/api/v1/scans", json={"domain": "hair"}, headers=h)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "consent_required"


def test_low_quality_image_is_rejected_and_blocks_analysis(client):
    h = _auth(client, "lowq@example.com")
    _grant_consent(client, h)
    sid = client.post("/api/v1/scans", json={"domain": "hair"}, headers=h).json()["session_id"]

    # A tiny image fails the resolution/detail check.
    tiny = _jpeg(64)
    r = client.post(
        f"/api/v1/scans/{sid}/images/upload",
        data={"view": "front_hairline"},
        files={"file": ("x.jpg", tiny, "image/jpeg")},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["overall_pass"] is False
    assert r.json()["retake_guidance"], "a failed image must tell the user how to fix it"

    # Analysis must refuse to run on an incomplete/failed set.
    r = client.post(f"/api/v1/scans/{sid}/analyze", headers=h)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "views_incomplete"


def test_full_hair_scan_produces_grounded_non_prescription_result(client):
    h = _auth(client, "full@example.com")
    _grant_consent(client, h)
    created = client.post("/api/v1/scans", json={"domain": "hair"}, headers=h).json()
    sid = created["session_id"]
    assert len(created["required_views"]) == 7

    good = _jpeg()
    for view in created["required_views"]:
        r = client.post(
            f"/api/v1/scans/{sid}/images/upload",
            data={"view": view},
            files={"file": ("x.jpg", good, "image/jpeg")},
            headers=h,
        )
        assert r.json()["overall_pass"] is True, r.json()["reasons"]

    assert client.post(f"/api/v1/scans/{sid}/analyze", headers=h).status_code == 200
    result = client.get(f"/api/v1/scans/{sid}/result", headers=h).json()

    assert result["observations"], "expected structured observations"
    for o in result["observations"]:
        # Never fabricate: every observation carries confidence + provenance.
        assert 0.0 <= o["confidence"] <= 1.0
        assert o["confidence_basis"]
        assert o["model_version"]
        assert o["observation_type"] in ("visual_observation", "ai_inference")

    # No prescriptions, ever.
    for rec in result["recommendations"]:
        assert rec["is_prescription"] is False

    # Mock inference must be disclosed.
    assert any("mock" in d.lower() for d in result["disclaimers"])
    assert result["safety_verdict"] is not None


def _complete_scan(client, headers, domain="hair"):
    created = client.post("/api/v1/scans", json={"domain": domain}, headers=headers).json()
    sid = created["session_id"]
    good = _jpeg()
    for view in created["required_views"]:
        client.post(
            f"/api/v1/scans/{sid}/images/upload",
            data={"view": view},
            files={"file": ("x.jpg", good, "image/jpeg")},
            headers=headers,
        )
    return sid


def test_self_reported_red_flag_forces_referral_and_suppresses_cosmetic(client):
    """The safety net must work even when the CV stack cannot see the sign.

    A user reporting scalp pustules must produce a referral-only result — no
    care guidance, no ingredient suggestions.
    """
    h = _auth(client, "redflag@example.com")
    _grant_consent(client, h)
    sid = _complete_scan(client, h, "hair")

    r = client.post(
        f"/api/v1/scans/{sid}/analyze",
        json={"hair_symptoms": {"pustules": True}},
        headers=h,
    )
    assert r.status_code == 200

    result = client.get(f"/api/v1/scans/{sid}/result", headers=h).json()
    assert result["safety_verdict"]["verdict"] == "refer"
    assert result["safety_verdict"]["suppressed_cosmetic"] is True

    types = {rec["type"] for rec in result["recommendations"]}
    assert types == {"referral"}, f"cosmetic advice leaked through: {types}"


def test_no_symptoms_reported_allows_normal_guidance(client):
    h = _auth(client, "nosymptom@example.com")
    _grant_consent(client, h)
    sid = _complete_scan(client, h, "hair")

    client.post(f"/api/v1/scans/{sid}/analyze", json={}, headers=h)
    result = client.get(f"/api/v1/scans/{sid}/result", headers=h).json()

    assert result["safety_verdict"]["verdict"] != "refer"
    assert any(rec["type"] != "referral" for rec in result["recommendations"])


def test_analyze_works_without_a_symptom_body(client):
    """The symptom report is optional — omitting it must not break analysis."""
    h = _auth(client, "nobody@example.com")
    _grant_consent(client, h)
    sid = _complete_scan(client, h, "hair")
    assert client.post(f"/api/v1/scans/{sid}/analyze", headers=h).status_code == 200


def test_image_content_requires_ownership(client):
    h1 = _auth(client, "owner@example.com")
    _grant_consent(client, h1)
    sid = client.post("/api/v1/scans", json={"domain": "hair"}, headers=h1).json()["session_id"]
    client.post(
        f"/api/v1/scans/{sid}/images/upload",
        data={"view": "front_hairline"},
        files={"file": ("x.jpg", _jpeg(), "image/jpeg")},
        headers=h1,
    )
    # The owner can read it.
    assert client.get(f"/api/v1/scans/{sid}/images/front_hairline/content", headers=h1).status_code == 200
    # Another user cannot.
    h2 = _auth(client, "intruder@example.com")
    assert client.get(f"/api/v1/scans/{sid}/images/front_hairline/content", headers=h2).status_code == 404
    # Nor can an anonymous caller.
    assert client.get(f"/api/v1/scans/{sid}/images/front_hairline/content").status_code == 401
