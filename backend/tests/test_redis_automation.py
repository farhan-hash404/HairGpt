"""Redis-backed counters/cache and the n8n automation webhooks."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import cache
from app.db.base import Base


@pytest.fixture
def fake_redis():
    client = fakeredis.FakeRedis()
    cache.set_redis_client(client)
    yield client
    cache.set_redis_client(None)


def test_counters_live_in_redis_when_available(fake_redis):
    assert cache.incr("rl:test:user:1", ttl=60) == 1
    assert cache.incr("rl:test:user:1", ttl=60) == 2
    assert 0 < fake_redis.ttl("rl:test:user:1") <= 60  # the window expires


def test_cache_round_trips_through_redis(fake_redis):
    cache.cache_set("qa:abc", {"answer": "x"}, ttl=100)
    assert cache.cache_get("qa:abc") == {"answer": "x"}
    assert fake_redis.exists("qa:abc")


def test_memory_fallback_without_redis():
    cache.set_redis_client(None)
    cache.cache_set("k", [1, 2], ttl=100)
    assert cache.cache_get("k") == [1, 2]
    assert cache.incr("c", ttl=60) == 1 and cache.incr("c", ttl=60) == 2


def test_webhooks_are_disabled_without_a_secret(client):
    assert client.post("/api/v1/automation/reminders").status_code == 404


def test_webhooks_require_the_shared_secret(client, monkeypatch):
    from app.api.routers import automation

    monkeypatch.setattr(automation.settings, "automation_webhook_secret", "s3cret")
    assert client.post("/api/v1/automation/reminders").status_code == 401
    ok = client.post("/api/v1/automation/reminders", headers={"X-HairGPT-Webhook-Secret": "s3cret"})
    assert ok.status_code == 200 and "reminders" in ok.json()


def test_due_reminders_selects_overdue_scans_and_missed_adherence():
    from app.models.scan import ScanSession
    from app.models.treatment import Treatment
    from app.models.user import User
    from app.worker import due_reminders

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    overdue = User(email="old@example.com", password_hash="x", display_name="Old")
    recent = User(email="new@example.com", password_hash="x", display_name="New")
    db.add_all([overdue, recent])
    db.flush()
    now = datetime.now(timezone.utc)
    db.add_all([
        ScanSession(user_id=overdue.id, domain="hair", status="complete", created_at=now - timedelta(days=40)),
        ScanSession(user_id=recent.id, domain="hair", status="complete", created_at=now - timedelta(days=5)),
        Treatment(user_id=recent.id, category="topical", name="Minoxidil foam", start_date=date.today()),
    ])
    db.commit()

    items = due_reminders(db)
    kinds = {(r["email"], r["kind"]) for r in items}
    assert ("old@example.com", "scan_due") in kinds
    assert ("new@example.com", "scan_due") not in kinds
    assert ("new@example.com", "adherence_log") in kinds
    # Minimal data only: nothing clinical leaves HairGPT.
    assert all(set(r) <= {"email", "name", "kind", "days_since_last_scan", "treatment"} for r in items)
