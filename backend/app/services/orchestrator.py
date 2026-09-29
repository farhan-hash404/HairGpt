"""Compatibility entry point for scan analysis.

The pipeline itself now lives in ``app/agents/analysis.py`` as a LangGraph
state machine (perceive -> confidence gate -> safety -> recommend/referral ->
explain -> audit -> persist). This module keeps the original call signature
for existing callers and tests.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.analysis import compute_overall_confidence, run_analysis_graph  # noqa: F401 - re-exported
from app.models.scan import Analysis, ScanSession


def run_analysis(db: Session, session: ScanSession, safety_ctx: dict | None = None) -> Analysis:
    """Run the full, non-interactive pipeline and return the persisted Analysis."""
    run_analysis_graph(db, session, safety_ctx, interactive=False)
    return db.scalar(select(Analysis).where(Analysis.session_id == session.id))
