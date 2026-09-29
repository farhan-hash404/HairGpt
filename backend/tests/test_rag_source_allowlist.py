"""Provenance: every piece of evidence must be allowlisted, licensed and traceable."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.models.evidence import EvidenceDocument
from app.rag.index import load_corpus
from app.rag.ingest import ensure_evidence
from app.rag.retriever import retrieve
from app.rag.sources import ALLOWED_SOURCES, EUROPEPMC_ALLOWED_LICENSES, PUBLISHERS


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    ensure_evidence(s)
    yield s
    s.close()


def test_social_media_source_is_rejected(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(json.dumps({
        "doc_id": "instagram:miracle", "source": "instagram", "title": "miracle cure",
        "url": "https://example.com", "content_hash": "x", "sections": [{"heading": "", "text": "buy this"}],
    }) + "\n", encoding="utf-8")
    assert load_corpus(corpus) == []


def test_every_indexed_document_is_allowlisted_and_licensed(db):
    docs = db.scalars(select(EvidenceDocument)).all()
    assert docs
    for d in docs:
        assert d.source in ALLOWED_SOURCES
        assert d.url.startswith("https://")
        assert d.license and d.attribution, f"{d.doc_key} lacks licence/attribution"


def test_published_licences_permit_redistribution():
    for publisher in PUBLISHERS.values():
        assert publisher.license.redistributable
    # Non-commercial and no-derivatives Creative Commons variants are excluded.
    assert not any("nc" in key or "nd" in key for key in EUROPEPMC_ALLOWED_LICENSES)


def test_full_corpus_is_licensed_and_skips_dosing_sections():
    """Checks the committed corpus file itself, not just the test subset."""
    from pathlib import Path

    full = Path(__file__).resolve().parents[1] / "data" / "corpus" / "documents.jsonl"
    for line in full.read_text(encoding="utf-8").splitlines():
        doc = json.loads(line)
        assert doc["source"] in ALLOWED_SOURCES
        assert doc["license"] and doc["attribution"]
        for section in doc["sections"]:
            heading = section["heading"].lower()
            assert "how and when to take" not in heading and "dosage" not in heading
            assert heading != "directions"


def test_retrieval_returns_traceable_refs(db):
    refs = retrieve(db, "hair thinning scalp care", "hair")
    assert refs
    for r in refs:
        assert r.url and r.source and r.title and r.license
        assert r.text  # the quoted passage itself


def test_corpus_file_setting_points_at_the_test_subset():
    # Guard against the unit tests accidentally running on the full corpus.
    assert settings.corpus_file.endswith("corpus_subset.jsonl")
