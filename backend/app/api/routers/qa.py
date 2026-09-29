from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.qa import answer_question
from app.api.deps import get_current_user
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.llm.chat import provider_info
from app.models.evidence import EvidenceDocument
from app.models.user import User

router = APIRouter(prefix="/qa", tags=["evidence Q&A"])


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=600)


@router.post("/ask")
def ask(
    body: AskIn,
    user: User = Depends(get_current_user),
    _limit: None = Depends(rate_limit("qa", per_minute=12)),
):
    """Answer a hair or scalp question ONLY from the evidence corpus.

    Every factual sentence is cited and machine-verified against its source;
    unverifiable answers are withheld rather than shown. Emergencies, prompt
    injection and dose requests are handled by deterministic guardrails before
    any model runs.
    """
    return answer_question(body.question)


@router.get("/sources")
def sources(db: Session = Depends(get_db)):
    """Every document the assistant may cite, with its licence."""
    docs = db.scalars(select(EvidenceDocument).order_by(EvidenceDocument.source, EvidenceDocument.title)).all()
    return {
        "count": len(docs),
        "documents": [
            {
                "key": d.doc_key, "title": d.title, "publisher": d.publisher, "source": d.source,
                "url": d.url, "license": d.license, "evidence_grade": d.evidence_grade,
                "last_reviewed": d.pub_date.isoformat() if d.pub_date else None,
                "chunks": len(d.chunks),
            }
            for d in docs
        ],
    }


@router.get("/model")
def model():
    """Which language model (if any) is answering. With none, answers are
    extractive: verbatim quotes, each cited."""
    info = provider_info()
    return {"provider": info.provider, "model": info.model, "available": info.available, "note": info.reason}
