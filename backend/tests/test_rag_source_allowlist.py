from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.evidence import EvidenceDocument
from app.rag.ingest import ingest_document, seed_corpus
from app.rag.retriever import retrieve


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def test_social_media_source_is_rejected(db):
    doc = {"source": "instagram", "title": "miracle cure", "text": "buy this", "domain": "hair"}
    assert ingest_document(db, doc) is None
    assert db.scalar(select(EvidenceDocument)) is None


def test_seed_corpus_only_contains_allowed_sources(db):
    seed_corpus(db)
    from app.models.evidence import ALLOWED_SOURCES

    for d in db.scalars(select(EvidenceDocument)).all():
        assert d.source in ALLOWED_SOURCES


def test_retrieval_returns_traceable_refs(db):
    seed_corpus(db)
    refs = retrieve(db, "hair thinning scalp care", "hair")
    assert refs
    for r in refs:
        assert r.url and r.source and r.title  # every claim is traceable
