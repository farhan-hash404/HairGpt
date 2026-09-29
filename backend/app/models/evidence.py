from __future__ import annotations

import uuid

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, JSONType, new_uuid, utcnow
from app.rag.sources import ALLOWED_SOURCES  # noqa: F401 - re-exported for callers


class EvidenceDocument(Base):
    """One source document in the evidence corpus — the system of record.

    Vectors do not live here: ChromaDB holds the dense index and BM25 is built in
    memory from the chunks below. This table is what every citation resolves to,
    so it carries the full provenance: URL, publisher, licence and attribution.
    """

    __tablename__ = "evidence_documents"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    # Stable key from the corpus file (e.g. "NHS:hair-loss"); makes rebuilds idempotent.
    doc_key: Mapped[str | None] = mapped_column(String(80), unique=True, index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(24), nullable=False)  # must be in ALLOWED_SOURCES
    source_type: Mapped[str] = mapped_column(String(16), default="scraped")  # scraped | curated
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(String, default="")
    publisher: Mapped[str] = mapped_column(String(160), default="")
    pub_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidence_grade: Mapped[str] = mapped_column(String(32), default="")
    license: Mapped[str] = mapped_column(String(48), default="")
    license_url: Mapped[str] = mapped_column(String, default="")
    attribution: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    domain: Mapped[str] = mapped_column(String(8), default="hair")  # hair | skin | both
    deprecated: Mapped[bool] = mapped_column(Boolean, default=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chunks: Mapped[list["EvidenceChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("evidence_documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str] = mapped_column(String(300), default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped["EvidenceDocument"] = relationship(back_populates="chunks")
