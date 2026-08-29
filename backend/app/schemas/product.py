from __future__ import annotations

import uuid

from pydantic import BaseModel


class IngredientOut(BaseModel):
    name: str
    is_active: bool
    concentration: str | None = None
    is_potential_irritant: bool = False
    duplicate_of: str | None = None


class ProductScanIn(BaseModel):
    image_storage_key: str


class ProductOut(BaseModel):
    id: uuid.UUID | None = None
    name: str
    manufacturer: str | None = None
    expiry: str | None = None
    batch: str | None = None
    source: str
    confidence: float
    ingredients: list[IngredientOut] = []
    duplicated_ingredients: list[str] = []
    potential_irritants: list[str] = []

    model_config = {"from_attributes": True}


class ProductRecommendIn(BaseModel):
    goals: list[str] = []
    budget: str | None = None
    regimen_product_ids: list[uuid.UUID] = []
    domain: str = "skin"
