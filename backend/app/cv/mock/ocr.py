from __future__ import annotations

import re

from app.cv.base import OCRExtractor
from app.cv.types import ConfidenceScore, ImageInput, OCRResult

try:  # pragma: no cover
    import pytesseract  # noqa
    from PIL import Image  # noqa
    import io as _io

    _HAS_OCR = True
except Exception:  # pragma: no cover
    _HAS_OCR = False

# Small demonstrative irritant/active reference lists (extend in production).
_KNOWN_ACTIVES = {"minoxidil", "ketoconazole", "salicylic acid", "niacinamide", "retinol", "adapalene", "zinc pyrithione"}
_KNOWN_IRRITANTS = {"fragrance", "parfum", "alcohol denat", "menthol", "sodium lauryl sulfate", "sls"}


def _parse_fields(text: str) -> dict:
    lower = text.lower()
    ingredients: list[dict] = []
    seen: set[str] = set()
    # crude ingredient split after "ingredients:"
    m = re.search(r"ingredients?[:\-]\s*(.+)", lower, re.DOTALL)
    ing_blob = m.group(1) if m else lower
    for raw in re.split(r"[,\n;]", ing_blob):
        name = raw.strip()
        if not name or len(name) > 60:
            continue
        dup = name in seen
        seen.add(name)
        ingredients.append(
            {
                "name": name,
                "is_active": any(a in name for a in _KNOWN_ACTIVES),
                "concentration": (re.search(r"\d+(\.\d+)?\s?%", name) or [None])[0]
                if re.search(r"\d+(\.\d+)?\s?%", name) else None,
                "is_potential_irritant": any(i in name for i in _KNOWN_IRRITANTS),
                "duplicate_of": name if dup else None,
            }
        )
        if len(ingredients) >= 60:
            break
    exp = re.search(r"(exp\w*)[:\s]*([0-9]{2}[/\-][0-9]{2,4})", lower)
    batch = re.search(r"(batch|lot)[:\s#]*([a-z0-9\-]+)", lower)
    return {
        "name": text.strip().split("\n")[0][:120] if text.strip() else "",
        "manufacturer": None,
        "expiry": exp.group(2) if exp else None,
        "batch": batch.group(2) if batch else None,
        "ingredients": ingredients,
    }


class MockOCRExtractor(OCRExtractor):
    """Product-label extraction. Uses pytesseract when available; otherwise returns
    confidence 0 and requests manual entry (never fabricates ingredients)."""

    VERSION = "mock-ocr@0.1"

    def extract(self, img: ImageInput) -> OCRResult:
        if _HAS_OCR:
            try:
                image = Image.open(_io.BytesIO(img.data))
                text = pytesseract.image_to_string(image)
                fields = _parse_fields(text)
                conf = 0.6 if text.strip() else 0.1
                return OCRResult(
                    raw_text=text,
                    fields=fields,
                    confidence=ConfidenceScore(conf, "tesseract OCR", self.VERSION).clamp(),
                    is_mock=True,
                )
            except Exception:
                pass
        return OCRResult(
            raw_text="",
            fields={"name": "", "manufacturer": None, "expiry": None, "batch": None, "ingredients": []},
            confidence=ConfidenceScore(0.0, "no OCR engine available; manual entry required", self.VERSION),
            is_mock=True,
        )
