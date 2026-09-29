"""Celery worker: background analysis, weekly corpus refresh, daily reminders.

    celery -A app.worker worker --loglevel=info          # process tasks
    celery -A app.worker beat --loglevel=info            # schedule periodic tasks

With REDIS_URL set, Redis is the broker and result backend. Without it (a
single-container demo host) tasks run eagerly in-process, so every code path
still works — it just stops being asynchronous.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import func, select

from app.core.config import settings

log = logging.getLogger("hairgpt.worker")

celery_app = Celery("hairgpt", broker=settings.redis_url or "memory://", backend=settings.redis_url or None)
celery_app.conf.update(
    task_always_eager=not settings.redis_url,
    task_eager_propagates=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,  # a crashed worker's task is redelivered, not lost
    worker_prefetch_multiplier=1,  # analyses are heavy; don't hoard them
    timezone="UTC",
    beat_schedule={
        "refresh-evidence-corpus": {"task": "hairgpt.refresh_corpus", "schedule": crontab(day_of_week="sun", hour=3)},
        "compute-reminders": {"task": "hairgpt.compute_reminders", "schedule": crontab(hour=8, minute=0)},
    },
)

SCAN_INTERVAL_DAYS = 30


def _session():
    from app.db import session as db_session

    return db_session.SessionLocal()


@celery_app.task(name="hairgpt.analyze_scan", bind=True, max_retries=2, default_retry_delay=10)
def analyze_scan(self, session_id: str, safety_ctx: dict | None = None) -> dict:
    """Run the LangGraph analysis in the background. Clients poll
    GET /scans/{id}/result, which answers 202 until the analysis is persisted."""
    import uuid

    from app.agents.analysis import run_analysis_graph
    from app.models.scan import ScanSession

    db = _session()
    try:
        scan = db.get(ScanSession, uuid.UUID(session_id))
        if scan is None:
            return {"status": "missing", "session_id": session_id}
        return run_analysis_graph(db, scan, safety_ctx or {}, interactive=False)
    except Exception as exc:
        log.exception("analysis failed for %s", session_id)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(name="hairgpt.refresh_corpus")
def refresh_corpus(pmc_per_topic: int = 3) -> dict:
    """Re-scrape the allowlisted sources and reconcile the index incrementally.

    Uses the HTTP cache, so unchanged pages cost nothing; only documents whose
    content hash changed are re-chunked and re-embedded.
    """
    from app.rag.index import get_rag_index
    from app.rag.scraper.run import build

    docs = asyncio.run(build(pmc_per_topic, refresh=True))
    db = _session()
    try:
        info = get_rag_index().ensure(db)
    finally:
        db.close()
    return {"documents": len(docs), "index": {k: info.get(k) for k in ("added", "updated", "removed", "chunks")}}


def due_reminders(db, today: date | None = None) -> list[dict]:
    """Users whose last completed scan is at least SCAN_INTERVAL_DAYS old, plus
    those with an active treatment and no adherence log in the last 3 days.

    Returns the minimum needed to send a reminder — no health data leaves.
    """
    from app.models.scan import ScanSession
    from app.models.treatment import AdherenceLog, Treatment
    from app.models.user import User

    today = today or datetime.now(timezone.utc).date()
    reminders: list[dict] = []
    last_scan = (
        select(ScanSession.user_id, func.max(ScanSession.created_at).label("last"))
        .where(ScanSession.status == "complete")
        .group_by(ScanSession.user_id)
        .subquery()
    )
    for user, last in db.execute(select(User, last_scan.c.last).join(last_scan, User.id == last_scan.c.user_id)).all():
        last_day = last.date() if isinstance(last, datetime) else last
        if last_day and (today - last_day).days >= SCAN_INTERVAL_DAYS:
            reminders.append({"email": user.email, "name": user.display_name or "there", "kind": "scan_due",
                              "days_since_last_scan": (today - last_day).days})

    since = today - timedelta(days=3)
    for treatment in db.scalars(select(Treatment).where(Treatment.end_date.is_(None))).all():
        recent = db.scalar(select(func.count(AdherenceLog.id)).where(
            AdherenceLog.treatment_id == treatment.id, AdherenceLog.date >= since))
        if not recent:
            user = db.get(User, treatment.user_id)
            if user:
                reminders.append({"email": user.email, "name": user.display_name or "there",
                                  "kind": "adherence_log", "treatment": treatment.name})
    return reminders


@celery_app.task(name="hairgpt.compute_reminders")
def compute_reminders() -> dict:
    db = _session()
    try:
        reminders = due_reminders(db)
    finally:
        db.close()
    return {"count": len(reminders)}
