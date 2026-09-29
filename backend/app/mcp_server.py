"""HairGPT's evidence tools over the Model Context Protocol.

Any MCP client (Claude Desktop, Claude Code, an IDE agent) can search the
licensed hair-health corpus and ask cited, machine-verified questions, through
the same retrieval, guardrails and hallucination gate as the web app. Every
tool is read-only; none can see users, scans or photos.

Run over stdio:
    python -m app.mcp_server
Register with Claude Code (from backend/):
    claude mcp add hairgpt -- .venv/Scripts/python.exe -m app.mcp_server
"""

from __future__ import annotations

import contextlib
import sys
import threading

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from sqlalchemy import select

from app.agents.qa import answer_question
from app.core.config import settings
from app.db import session as db_session
from app.models.evidence import EvidenceDocument
from app.rag.ingest import ensure_evidence
from app.rag.retriever import is_supported, search_chunks

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
MAX_QUERY = 600

SAFETY_POLICY = """\
HairGPT evidence tools: usage policy

The corpus is general health information from the NHS (OGL v3), MedlinePlus,
NIAMS and DailyMed (US public domain) and open-access reviews (CC BY / CC0).

- Information, not diagnosis. Never tell a person which condition they have.
- No doses, and no instruction to start, stop or change a medicine; point to a
  GP, pharmacist or dermatologist instead.
- Quote passages verbatim and cite their URL. If search says a question is not
  supported by the corpus, say so rather than answering from memory.
- Sudden patchy loss, scarring, scalp pain, rash or systemic symptoms warrant a
  clinician. Swelling of the face or throat, or difficulty breathing, is an
  emergency (999 / 911 / 112).
"""

mcp = MCPServer(
    name="hairgpt-evidence",
    title="HairGPT evidence",
    version="1.0.0",
    instructions=(
        "Tools for grounded hair and scalp health information. Prefer ask_hair_question for a "
        "verified, cited answer; use search_hair_evidence for raw passages. Read the "
        "hairgpt://safety-policy resource before answering people: no diagnoses, no doses."
    ),
)

_bootstrap_lock = threading.Lock()
_bootstrapped = False


def _bootstrap() -> None:
    """Make sure the evidence tables and search index exist (idempotent)."""
    global _bootstrapped
    with _bootstrap_lock:
        if _bootstrapped:
            return
        if not settings.is_prod:
            db_session.init_db()
        db = db_session.SessionLocal()
        try:
            ensure_evidence(db)
        finally:
            db.close()
        _bootstrapped = True


@mcp.tool(annotations=READ_ONLY)
def search_hair_evidence(query: str, k: int = 5) -> dict:
    """Search the licensed hair and scalp health corpus.

    Returns up to k ranked passages (at most two per document), each with its
    publisher, URL, licence, evidence grade and a `supported` flag saying whether
    it genuinely bears on the query. Passages are information, not advice.
    """
    _bootstrap()
    query = query.strip()[:MAX_QUERY]
    db = db_session.SessionLocal()
    try:
        chunks = search_chunks(db, query, "hair", k=max(1, min(k, 10)), per_doc=2)
    finally:
        db.close()
    results = [
        {
            "rank": i,
            "title": c.title,
            "section": c.section,
            "publisher": c.publisher,
            "url": c.url,
            "license": c.license,
            "evidence_grade": c.evidence_grade,
            "supported": is_supported(c),
            "similarity": c.similarity,
            "passage": c.text,
        }
        for i, c in enumerate(chunks, start=1)
    ]
    return {"query": query, "supported": any(r["supported"] for r in results), "results": results}


@mcp.tool(annotations=READ_ONLY)
def ask_hair_question(question: str) -> dict:
    """Answer a hair or scalp question only from the evidence corpus.

    Every factual sentence carries a [n] citation that has been checked against
    its source; answers that fail the check are withheld. Emergencies, dose
    requests and prompt injection get fixed safe replies. `mode` says how the
    answer was produced: llm, extractive (verbatim quotes), abstain, guardrail
    or withheld.
    """
    _bootstrap()
    result = answer_question(question.strip()[:MAX_QUERY])
    return {
        "answer": result["answer"],
        "mode": result["mode"],
        "abstained": result["abstained"],
        "verified": bool(result.get("audit", {}).get("passed")) if result.get("audit") else None,
        "citations": [
            {k: c[k] for k in ("n", "title", "section", "publisher", "url", "license", "quote")}
            for c in result["citations"]
        ],
        "model": result["model"],
    }


@mcp.tool(annotations=READ_ONLY)
def list_sources() -> dict:
    """Every document the tools can cite, with publisher, licence and review date."""
    _bootstrap()
    db = db_session.SessionLocal()
    try:
        docs = db.scalars(select(EvidenceDocument).order_by(EvidenceDocument.source, EvidenceDocument.title)).all()
        documents = [
            {
                "title": d.title, "publisher": d.publisher, "url": d.url, "license": d.license,
                "evidence_grade": d.evidence_grade,
                "last_reviewed": d.pub_date.isoformat() if d.pub_date else None,
            }
            for d in docs
        ]
    finally:
        db.close()
    return {"count": len(documents), "documents": documents}


@mcp.resource("hairgpt://safety-policy", name="safety-policy", mime_type="text/plain")
def safety_policy() -> str:
    """What these tools must never be used to do."""
    return SAFETY_POLICY


def main() -> None:
    # Over stdio, stdout IS the protocol channel: anything printed while the
    # index loads (model downloads, library banners) must go to stderr.
    with contextlib.redirect_stdout(sys.stderr):
        _bootstrap()
    mcp.run("stdio")


if __name__ == "__main__":
    main()
