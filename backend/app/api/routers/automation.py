"""Webhooks for workflow automation (n8n).

n8n owns scheduling and delivery (email, Slack); HairGPT owns the data. The
workflow in ``automation/n8n/hairgpt-workflows.json`` calls these endpoints on
a timer. They are authenticated with a shared secret rather than a user token,
compared in constant time, and disabled entirely when no secret is set.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(prefix="/automation", tags=["automation (n8n)"])


def require_webhook_secret(x_hairgpt_webhook_secret: str | None = Header(default=None)) -> None:
    expected = settings.automation_webhook_secret
    if not expected:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "automation webhooks are disabled")
    if not x_hairgpt_webhook_secret or not hmac.compare_digest(x_hairgpt_webhook_secret, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid webhook secret")


@router.post("/reminders", dependencies=[Depends(require_webhook_secret)])
def reminders(db: Session = Depends(get_db)):
    """Who should get a reminder today. Contains no health data beyond the
    reminder type — n8n only needs an address and a message."""
    from app.worker import due_reminders

    items = due_reminders(db)
    return {"count": len(items), "reminders": items}


@router.post("/corpus-refresh", dependencies=[Depends(require_webhook_secret)])
def corpus_refresh():
    """Queue a re-scrape of the evidence sources (runs inline without Redis)."""
    from app.worker import refresh_corpus

    task = refresh_corpus.delay()
    return {"queued": True, "task_id": task.id, "eager": not settings.redis_url}
