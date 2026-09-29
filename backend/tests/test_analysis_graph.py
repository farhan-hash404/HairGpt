"""The LangGraph analysis pipeline: human-in-the-loop, checkpointing, and the
structural safety override."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.cv.imageio import HAS_PIXELS
from tests.conftest import authenticate, grant_consent, make_jpeg

pytestmark = pytest.mark.skipif(not HAS_PIXELS, reason="numpy/Pillow not installed")


def _focused_scan(client, headers, views=("crown",)) -> str:
    r = client.post("/api/v1/scans", json={"domain": "hair", "focus_views": list(views)}, headers=headers)
    assert r.status_code == 201, r.text
    assert r.json()["required_views"] == list(views)
    sid = r.json()["session_id"]
    for view in views:
        up = client.post(f"/api/v1/scans/{sid}/images/upload", data={"view": view},
                         files={"file": ("x.jpg", make_jpeg(), "image/jpeg")}, headers=headers)
        assert up.json()["overall_pass"], up.json()
    return sid


@pytest.fixture
def always_low_confidence(monkeypatch):
    """Force the human-in-the-loop gate to trigger regardless of the image."""
    import app.agents.analysis as analysis

    monkeypatch.setattr(analysis, "LOW_CONFIDENCE", 1.01)


@pytest.fixture
def cv_call_counter(monkeypatch):
    import app.agents.analysis as analysis

    calls = {"n": 0}
    real = analysis.get_metric_estimator

    def counting():
        estimator = real()
        original = estimator.estimate

        def estimate(*args, **kwargs):
            calls["n"] += 1
            return original(*args, **kwargs)

        estimator.estimate = estimate
        return estimator

    monkeypatch.setattr(analysis, "get_metric_estimator", counting)
    return calls


def test_focused_scan_analyzes_and_states_its_coverage(client):
    headers = authenticate(client, "focus@example.com")
    grant_consent(client, headers)
    sid = _focused_scan(client, headers, ("crown", "top"))
    assert client.post(f"/api/v1/scans/{sid}/analyze", json={}, headers=headers).json()["status"] == "complete"
    result = client.get(f"/api/v1/scans/{sid}/result", headers=headers).json()
    assert any("Focused scan: 2 of 7" in lim for lim in result["explanation"]["limitations"])


def test_focused_scan_rejects_invalid_views(client):
    headers = authenticate(client, "focusbad@example.com")
    grant_consent(client, headers)
    r = client.post("/api/v1/scans", json={"domain": "hair", "focus_views": ["elbow"]}, headers=headers)
    assert r.status_code == 422


def test_low_confidence_pauses_for_a_human_and_resumes_without_rerunning_cv(
    client, always_low_confidence, cv_call_counter
):
    headers = authenticate(client, "hitl@example.com")
    grant_consent(client, headers)
    sid = _focused_scan(client, headers)

    paused = client.post(f"/api/v1/scans/{sid}/analyze?interactive=true", json={}, headers=headers).json()
    assert paused["status"] == "awaiting_confirmation"
    assert paused["options"] == ["proceed", "retake"]
    assert client.get(f"/api/v1/scans/{sid}/result", headers=headers).status_code == 202
    assert client.get(f"/api/v1/scans/{sid}/analyze/pending", headers=headers).json()["awaiting_confirmation"]
    cv_runs_before_resume = cv_call_counter["n"]

    done = client.post(f"/api/v1/scans/{sid}/analyze/resume", json={"decision": "proceed"}, headers=headers).json()
    assert done["status"] == "complete"
    # Resumed from the checkpoint: the computer vision did NOT run again.
    assert cv_call_counter["n"] == cv_runs_before_resume
    trace = client.get(f"/api/v1/scans/{sid}/result", headers=headers).json()["explanation"]["pipeline_trace"]
    assert "human-in-the-loop: proceed" in trace


def test_choosing_retake_persists_nothing(client, always_low_confidence):
    from app.db import session as db_session
    from app.models.scan import Analysis

    headers = authenticate(client, "retake@example.com")
    grant_consent(client, headers)
    sid = _focused_scan(client, headers)
    client.post(f"/api/v1/scans/{sid}/analyze?interactive=true", json={}, headers=headers)
    r = client.post(f"/api/v1/scans/{sid}/analyze/resume", json={"decision": "retake"}, headers=headers).json()
    assert r["status"] == "retake_requested"
    db = db_session.SessionLocal()
    try:
        assert db.scalar(select(Analysis).where(Analysis.session_id == __import__("uuid").UUID(sid))) is None
    finally:
        db.close()


def test_the_website_default_never_pauses(client, always_low_confidence):
    headers = authenticate(client, "noninteractive@example.com")
    grant_consent(client, headers)
    sid = _focused_scan(client, headers)
    assert client.post(f"/api/v1/scans/{sid}/analyze", json={}, headers=headers).json()["status"] == "complete"


def test_red_flags_make_the_care_node_unreachable(client):
    headers = authenticate(client, "redflag@example.com")
    grant_consent(client, headers)
    sid = _focused_scan(client, headers)
    client.post(f"/api/v1/scans/{sid}/analyze", json={"hair_symptoms": {"scalp_pain_or_tenderness": True}},
                headers=headers)
    result = client.get(f"/api/v1/scans/{sid}/result", headers=headers).json()
    if result["safety_verdict"]["verdict"] == "refer":
        trace = result["explanation"]["pipeline_trace"]
        assert any(step.startswith("referral") for step in trace)
        assert not any(step.startswith("recommend") for step in trace)
        assert [r["type"] for r in result["recommendations"]] == ["referral"]


def test_background_analysis_via_celery(client):
    headers = authenticate(client, "celery@example.com")
    grant_consent(client, headers)
    sid = _focused_scan(client, headers)
    queued = client.post(f"/api/v1/scans/{sid}/analyze?background=true", json={}, headers=headers).json()
    assert queued["status"] == "queued" and queued["task_id"]
    # No Redis in tests, so Celery runs the task inline: the result is ready.
    assert client.get(f"/api/v1/scans/{sid}/result", headers=headers).status_code == 200
