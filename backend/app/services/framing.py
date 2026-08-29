from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cv.imageio import DecodedImage
from app.models.scan import ScanImage, ScanSession
from app.services.storage import storage

log = logging.getLogger("hairgpt.framing")


def find_reference_session(db: Session, user_id, domain: str, exclude_session_id=None) -> ScanSession | None:
    """The most recent COMPLETED scan of the same domain, used as the capture
    reference so repeat scans are framed like the previous ones."""
    stmt = (
        select(ScanSession)
        .where(
            ScanSession.user_id == user_id,
            ScanSession.domain == domain,
            ScanSession.status == "complete",
        )
        .order_by(ScanSession.created_at.desc())
    )
    if exclude_session_id is not None:
        stmt = stmt.where(ScanSession.id != exclude_session_id)
    return db.scalars(stmt).first()


def reference_views(db: Session, session: ScanSession) -> list[str]:
    """Views in the reference scan that passed quality — only those are worth
    showing as a capture guide."""
    rows = db.scalars(
        select(ScanImage).where(
            ScanImage.session_id == session.id, ScanImage.quality_passed.is_(True)
        )
    ).all()
    return [img.view for img in rows]


_GRID = 8


def _layout_signature(data: bytes) -> list[float] | None:
    """A coarse spatial fingerprint of where light and dark fall in the frame.

    The image is reduced to an 8x8 grid of block means, then normalized to zero
    mean and unit variance. Normalizing makes the signature robust to overall
    brightness and contrast changes (different lighting) while remaining
    sensitive to *composition* — which is exactly what framing is.

    Returns None when no pixel decoder is available.
    """
    d = DecodedImage(data)
    if not d.real_pixels:
        return None

    g = d.gray
    h, w = g.shape
    sig: list[float] = []
    for by in range(_GRID):
        y0, y1 = int(by * h / _GRID), int((by + 1) * h / _GRID)
        for bx in range(_GRID):
            x0, x1 = int(bx * w / _GRID), int((bx + 1) * w / _GRID)
            block = g[y0:y1, x0:x1]
            sig.append(float(block.mean()) if block.size else 0.0)

    mean = sum(sig) / len(sig)
    centered = [v - mean for v in sig]
    variance = sum(v * v for v in centered) / len(centered)
    std = variance**0.5
    if std < 1e-6:
        # A perfectly flat frame carries no layout information at all.
        return None
    return [v / std for v in centered]


def _layout_similarity(a: list[float], b: list[float]) -> float:
    """Normalized correlation of two layout signatures, clamped to 0..1.

    1.0 = same composition, 0.0 = unrelated or inverted.
    """
    correlation = sum(x * y for x, y in zip(a, b)) / len(a)
    return round(max(0.0, min(1.0, correlation)), 3)


def compute_framing_match(db: Session, reference: ScanSession | None, view: str, data: bytes) -> float | None:
    """How closely a new capture is composed relative to the reference capture.

    Returns 0..1, or None when the comparison is NOT APPLICABLE — no reference
    scan (a first scan), no readable reference image, or a frame too flat to
    carry layout information. The caller must never treat None as a failure.

    This is a composition/layout proxy, not a clinical measure and not true pose
    estimation (which needs the landmark model in the real CV backend). It exists
    to keep repeat captures comparable, and it only ever warns.
    """
    if reference is None:
        return None

    ref_image = db.scalar(
        select(ScanImage).where(
            ScanImage.session_id == reference.id,
            ScanImage.view == view,
            ScanImage.quality_passed.is_(True),
        )
    )
    if ref_image is None:
        return None

    try:
        ref_bytes = storage.get(ref_image.storage_key)
    except Exception as exc:
        log.warning("framing: reference image unreadable (%s)", exc)
        return None

    try:
        ref_sig = _layout_signature(ref_bytes)
        new_sig = _layout_signature(data)
        if ref_sig is None or new_sig is None:
            return None
        return _layout_similarity(ref_sig, new_sig)
    except Exception as exc:
        log.warning("framing: could not compute match (%s)", exc)
        return None


# Below this, the capture is framed noticeably differently from last time.
FRAMING_WARN_THRESHOLD = 0.6

FRAMING_GUIDANCE = (
    "This shot is framed differently from your last scan. Match the ghost outline "
    "so the two can be compared reliably."
)
