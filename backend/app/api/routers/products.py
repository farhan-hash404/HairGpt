from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.cv.registry import get_ocr
from app.cv.types import ImageInput
from app.db.session import get_db
from app.models.product import Product, ProductIngredient
from app.models.user import User
from app.rag.retriever import retrieve
from app.schemas.product import IngredientOut, ProductOut, ProductRecommendIn, ProductScanIn
from app.services.storage import storage

router = APIRouter(prefix="/products", tags=["products"])

# Common incompatible / caution ingredient pairs (illustrative; extend in production).
_CONFLICTS = [
    ({"retinol", "tretinoin", "adapalene"}, {"benzoyl peroxide"}, "May reduce efficacy / increase irritation; use at different times."),
    ({"retinol", "tretinoin"}, {"salicylic acid", "glycolic acid"}, "Combining strong actives can irritate; introduce gradually."),
    ({"vitamin c", "ascorbic acid"}, {"niacinamide"}, "Generally fine, but sensitive skin may prefer separating them."),
]


@router.post("/scan", response_model=ProductOut)
def scan_product(body: ProductScanIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        data = storage.get(body.image_storage_key)
    except Exception:
        raise HTTPException(404, "Image not found for provided storage key")
    result = get_ocr().extract(ImageInput(data=data))
    fields = result.fields
    ingredients = fields.get("ingredients", [])
    dupes = sorted({i["name"] for i in ingredients if i.get("duplicate_of")})
    irritants = sorted({i["name"] for i in ingredients if i.get("is_potential_irritant")})
    return ProductOut(
        name=fields.get("name", ""),
        manufacturer=fields.get("manufacturer"),
        expiry=fields.get("expiry"),
        batch=fields.get("batch"),
        source="scan_ocr",
        confidence=result.confidence.value,
        ingredients=[IngredientOut(**{k: i.get(k) for k in ("name", "is_active", "concentration", "is_potential_irritant", "duplicate_of")}) for i in ingredients],
        duplicated_ingredients=dupes,
        potential_irritants=irritants,
    )


@router.post("", response_model=ProductOut, status_code=201)
def save_product(body: ProductOut, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = Product(
        user_id=user.id, name=body.name, manufacturer=body.manufacturer, expiry=body.expiry,
        batch=body.batch, source=body.source, confidence=body.confidence,
    )
    db.add(p)
    db.flush()
    for ing in body.ingredients:
        db.add(ProductIngredient(
            product_id=p.id, name=ing.name, is_active=ing.is_active, concentration=ing.concentration,
            is_potential_irritant=ing.is_potential_irritant, duplicate_of=ing.duplicate_of,
        ))
    db.commit()
    db.refresh(p)
    body.id = p.id
    return body


@router.get("", response_model=list[ProductOut])
def list_products(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    out = []
    for p in db.scalars(select(Product).where(Product.user_id == user.id)).all():
        out.append(ProductOut(
            id=p.id, name=p.name, manufacturer=p.manufacturer, expiry=p.expiry, batch=p.batch,
            source=p.source, confidence=p.confidence,
            ingredients=[IngredientOut(name=i.name, is_active=i.is_active, concentration=i.concentration,
                                       is_potential_irritant=i.is_potential_irritant, duplicate_of=i.duplicate_of)
                         for i in p.ingredients],
        ))
    return out


@router.post("/recommend")
def recommend(body: ProductRecommendIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Evidence-gated recommendations based on goals, regimen, and ingredient
    compatibility. Ranking NEVER uses affiliate revenue (no such field exists)."""
    # Gather current regimen ingredients.
    regimen_ings: set[str] = set()
    for pid in body.regimen_product_ids:
        p = db.get(Product, pid)
        if p and p.user_id == user.id:
            regimen_ings |= {i.name.lower() for i in p.ingredients}

    # Detect conflicts within the current regimen.
    conflicts = []
    for group_a, group_b, msg in _CONFLICTS:
        if regimen_ings & group_a and regimen_ings & group_b:
            conflicts.append({"between": sorted((regimen_ings & group_a) | (regimen_ings & group_b)), "note": msg})

    query = " ".join([body.domain] + body.goals) or body.domain
    domain = body.domain if body.domain in ("hair", "skin") else "hair"
    evidence = retrieve(db, query, domain, supported_only=True)

    suggestions = []
    for e in evidence[:4]:
        suggestions.append({
            "based_on": e.title,
            "source": e.source,
            "evidence_grade": e.evidence_grade,
            "suggestion": _suggestion_from_evidence(e.text),
            "url": e.url,
            # The passage itself, so every suggestion can be checked against its source.
            "quote": e.text[:400],
            "section": e.section,
            "license": e.license,
        })

    return {
        "goals": body.goals,
        "budget": body.budget,
        "ingredient_conflicts": conflicts,
        "evidence_backed_suggestions": suggestions,
        "ranking_basis": "evidence grade and goal match — never affiliate revenue",
        "disclaimer": "General, non-prescription guidance. Not a diagnosis.",
    }


def _suggestion_from_evidence(text: str) -> str:
    low = text.lower()
    if "sunscreen" in low:
        return "Include a daily broad-spectrum SPF 30+ sunscreen."
    if "moisturizer" in low or "barrier" in low:
        return "Add a fragrance-free moisturizer to support the skin barrier."
    if "ketoconazole" in low or "dandruff" in low:
        return "Consider an OTC antifungal/anti-dandruff shampoo used as directed."
    if "patch" in low:
        return "Patch-test new products and introduce one at a time."
    return "Follow the cited guidance; keep the regimen simple and evidence-based."
