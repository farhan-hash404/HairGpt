from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, JSONType, new_uuid, utcnow


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    manufacturer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expiry: Mapped[str | None] = mapped_column(String(32), nullable=True)
    batch: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")  # scan_ocr | manual
    raw_ocr: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ingredients: Mapped[list["ProductIngredient"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductIngredient(Base):
    __tablename__ = "product_ingredients"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    concentration: Mapped[str | None] = mapped_column(String(48), nullable=True)
    is_potential_irritant: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[str | None] = mapped_column(String(160), nullable=True)
    evidence_refs: Mapped[list] = mapped_column(JSONType, default=list)

    product: Mapped["Product"] = relationship(back_populates="ingredients")
