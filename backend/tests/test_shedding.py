"""Shedding log — the product's leading indicator between scans.

The statistical discipline here matters: shedding varies enormously with washing
and brushing, so a blended average would mostly measure how often someone washed
their hair. We compare like with like and refuse to call a trend on noise.
"""
from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import authenticate


def _auth(client):
    return authenticate(client, "shed@example.com")


def _log(client, headers, days_ago: int, count: int, context: str = "wash"):
    return client.post(
        "/api/v1/shedding",
        json={
            "date": (date.today() - timedelta(days=days_ago)).isoformat(),
            "count": count,
            "context": context,
        },
        headers=headers,
    )


def test_logging_and_listing(client):
    headers = _auth(client)
    assert _log(client, headers, 1, 60).status_code == 201
    entries = client.get("/api/v1/shedding", headers=headers).json()
    assert len(entries) == 1
    assert entries[0]["count"] == 60


def test_same_day_same_context_updates_rather_than_duplicates(client):
    headers = _auth(client)
    _log(client, headers, 0, 50)
    _log(client, headers, 0, 80)
    entries = client.get("/api/v1/shedding", headers=headers).json()
    assert len(entries) == 1
    assert entries[0]["count"] == 80


def test_same_day_different_context_is_a_separate_entry(client):
    """Wash-day and brush-day shedding are not the same measurement."""
    headers = _auth(client)
    _log(client, headers, 0, 120, context="wash")
    _log(client, headers, 0, 15, context="brush")
    assert len(client.get("/api/v1/shedding", headers=headers).json()) == 2


def test_bucket_only_entries_are_accepted(client):
    """Counting hairs is tedious; buckets keep logging low-friction."""
    headers = _auth(client)
    r = client.post("/api/v1/shedding", json={"bucket": "moderate", "context": "general"}, headers=headers)
    assert r.status_code == 201
    assert r.json()["bucket"] == "moderate"


def test_averages_are_reported_per_context(client):
    """A single blended average would be driven by wash frequency, not shedding."""
    headers = _auth(client)
    for i in range(4):
        _log(client, headers, i, 150, context="wash")
        _log(client, headers, i, 10, context="brush")

    trend = client.get("/api/v1/shedding/trend", headers=headers).json()
    assert trend["average_by_context"]["wash"] == 150.0
    assert trend["average_by_context"]["brush"] == 10.0


def test_refuses_to_call_a_trend_without_enough_data(client):
    headers = _auth(client)
    _log(client, headers, 1, 100)
    trend = client.get("/api/v1/shedding/trend", headers=headers).json()
    assert trend["trend"] == "insufficient_data"


def test_noise_is_reported_as_stable_not_a_trend(client):
    """Random variation must not be presented as a change."""
    headers = _auth(client)
    for i, value in enumerate([100, 104, 98, 103, 99, 101, 102, 100]):
        _log(client, headers, 20 - i, value)
    trend = client.get("/api/v1/shedding/trend", headers=headers).json()
    assert trend["trend"] == "stable"


def test_a_real_increase_is_detected(client):
    headers = _auth(client)
    for i, value in enumerate([40, 45, 42, 44, 130, 140, 135, 145]):
        _log(client, headers, 20 - i, value)
    trend = client.get("/api/v1/shedding/trend", headers=headers).json()
    assert trend["trend"] == "increasing"


def test_a_real_decrease_is_detected(client):
    headers = _auth(client)
    for i, value in enumerate([150, 145, 155, 148, 50, 45, 55, 48]):
        _log(client, headers, 20 - i, value)
    trend = client.get("/api/v1/shedding/trend", headers=headers).json()
    assert trend["trend"] == "decreasing"


def test_trend_always_carries_a_disclaimer(client):
    headers = _auth(client)
    trend = client.get("/api/v1/shedding/trend", headers=headers).json()
    assert "self-reported" in trend["disclaimer"].lower()
    assert "diagnose" in trend["disclaimer"].lower()


def test_shedding_is_scoped_to_its_owner(client):
    headers_a = authenticate(client, "sheda@example.com")
    _log(client, headers_a, 0, 99)
    headers_b = authenticate(client, "shedb@example.com")
    assert client.get("/api/v1/shedding", headers=headers_b).json() == []


def test_shedding_appears_in_the_doctor_report(client):
    from tests.conftest import complete_scan, grant_consent

    headers = authenticate(client, "shedreport@example.com")
    grant_consent(client, headers)
    _log(client, headers, 2, 85, context="wash")
    sid = complete_scan(client, headers, "hair")
    report = client.get(f"/api/v1/scans/{sid}/doctor-report", headers=headers).json()
    assert len(report["shedding_log_90d"]) == 1
    assert report["shedding_log_90d"][0]["count"] == 85
