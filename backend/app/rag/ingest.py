"""Entry point used at startup, by the demo seeder, and by tests.

The evidence corpus is the scraped, openly-licensed collection in
``data/corpus/documents.jsonl`` (built by ``python -m app.rag.scraper.run``).
The earlier hand-written seed summaries were retired: several cited only
generic URLs, which is exactly the weak provenance a grounded system must not
have. Every chunk now resolves to a specific page and licence.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.rag.index import get_rag_index


def ensure_evidence(db: Session, force: bool = False) -> dict:
    """Idempotently sync the corpus into SQL and the vector index."""
    return get_rag_index().ensure(db, force=force)
