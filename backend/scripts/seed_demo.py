"""Seed a demo account with synthetic scans, treatments and adherence.

Generates SYNTHETIC images (procedurally drawn hair/scalp texture) purely so the
UI and pipeline can be exercised end-to-end. These are not real people and carry
no clinical meaning whatsoever.

Usage (backend venv active, server NOT required â€” talks to the DB directly):
    python -m scripts.seed_demo
"""

from __future__ import annotations

import math
import random
import sys
from datetime import date, timedelta
from io import BytesIO

from app.api.routers.history import build_history_context
from app.core.security import hash_password
from app.cv.registry import get_quality_gate
from app.cv.types import ImageInput
from app.db.session import SessionLocal
from app.models.scan import ImageQualityReport, ScanImage, ScanSession
from app.models.history import ClinicalHistory, SheddingLog
from app.models.treatment import AdherenceLog, Treatment
from app.models.user import Consent, User
from app.rag.ingest import ensure_evidence
from app.services.orchestrator import run_analysis
from app.services.storage import make_storage_key, storage

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demopassword123"
HAIR_VIEWS = ["front_hairline", "left_temple", "right_temple", "top", "crown", "sides", "back"]


def synth_scalp_image(
    seed: int,
    scalp_ratio: float,
    size: int = 1024,
    offset: tuple[float, float] = (0.0, 0.0),
    zoom: float = 1.0,
) -> bytes:
    """Draw a synthetic head: an elliptical scalp region with a parting line and
    hair-strand texture, over a darker background.

    The elliptical subject and parting give the frame real SPATIAL STRUCTURE, so
    the framing metric has something meaningful to compare. `offset` and `zoom`
    shift/scale the subject to simulate a differently-framed capture.

    `scalp_ratio` (0..1) controls how much scalp shows through â€” this is what
    makes successive "scans" differ, so the timeline has real signal.
    """
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        sys.exit("Pillow is required for demo seeding: pip install Pillow")

    rng = random.Random(seed)
    img = Image.new("RGB", (size, size), (58, 56, 62))  # background, not skin
    d = ImageDraw.Draw(img)

    # Head/scalp ellipse, positioned by offset and scaled by zoom.
    cx = size * (0.5 + offset[0])
    cy = size * (0.5 + offset[1])
    rx = size * 0.38 * zoom
    ry = size * 0.44 * zoom
    bbox = [cx - rx, cy - ry, cx + rx, cy + ry]
    d.ellipse(bbox, fill=(206, 178, 158))  # scalp base tone

    # Directional lighting across the scalp so exposure stats look natural.
    for i in range(int(cy - ry), int(cy + ry), 4):
        t = (i - (cy - ry)) / max(1.0, 2 * ry)
        shade = int(16 * math.sin(t * math.pi))
        d.ellipse(
            [cx - rx, i, cx + rx, i + 4],
            fill=(206 - shade, 178 - shade, 158 - shade),
        )

    # Hair strands, confined to the scalp ellipse. Fewer strands => more scalp.
    n_strands = int(6000 * (1.0 - scalp_ratio))
    for _ in range(n_strands):
        # Rejection-sample inside the ellipse.
        px = rng.uniform(cx - rx, cx + rx)
        py = rng.uniform(cy - ry, cy + ry)
        if ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 > 1.0:
            continue
        length = rng.uniform(18, 46) * zoom
        angle = rng.uniform(-0.5, 0.5) + math.pi / 2
        tone = rng.randint(28, 74)
        d.line(
            [(px, py), (px + math.cos(angle) * length, py + math.sin(angle) * length)],
            fill=(tone, tone - 6, tone - 10),
            width=rng.choice([1, 1, 2]),
        )

    # A parting line: a consistent landmark that anchors framing.
    d.line([(cx, cy - ry * 0.85), (cx, cy + ry * 0.2)], fill=(214, 188, 168), width=max(2, int(6 * zoom)))

    img = img.filter(ImageFilter.GaussianBlur(0.4))  # slight softness, still sharp
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def ensure_user(db) -> User:
    user = db.query(User).filter(User.email == DEMO_EMAIL).one_or_none()
    if user:
        return user
    user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), display_name="Demo User")
    db.add(user)
    db.flush()
    for purpose in ("storage", "analysis", "longitudinal"):
        db.add(Consent(user_id=user.id, purpose=purpose, granted=True, granted_at=date.today()))
    db.commit()
    return user


def create_scan(db, user, days_ago: int, scalp_ratio: float, seed_base: int) -> ScanSession | None:
    session = ScanSession(user_id=user.id, domain="hair", capture_protocol="hair_v1", status="capturing")
    session.created_at = None  # let default apply, then override below
    db.add(session)
    db.flush()
    # Backdate so the timeline shows spread.
    from app.db.base import utcnow

    session.created_at = utcnow() - timedelta(days=days_ago)

    gate = get_quality_gate()
    passed = 0
    for i, view in enumerate(HAIR_VIEWS):
        data = synth_scalp_image(seed_base + i, scalp_ratio)
        key = make_storage_key(user.id, session.id, view)
        storage.put(key, data)
        report = gate.assess(ImageInput(data=data, view=view), view, "hair")

        image = ScanImage(session_id=session.id, view=view, storage_key=key, quality_passed=report.overall_pass)
        db.add(image)
        db.flush()
        db.add(
            ImageQualityReport(
                image_id=image.id,
                blur_score=report.blur_score,
                exposure_score=report.exposure_score,
                overexposed_frac=report.overexposed_frac,
                distance_ok=report.distance_ok,
                angle_ok=report.angle_ok,
                scalp_visibility=report.scalp_visibility,
                overall_pass=report.overall_pass,
                reasons=report.reasons,
                retake_guidance=report.retake_guidance,
                confidence=report.confidence.value,
                method=report.confidence.method,
                is_mock=report.is_mock,
            )
        )
        passed += int(report.overall_pass)
    db.commit()

    if passed < len(HAIR_VIEWS):
        print(f"  scan {days_ago}d ago: only {passed}/{len(HAIR_VIEWS)} views passed the quality gate â€” not analyzed")
        session.status = "rejected"
        db.commit()
        return None

    # Mirror the API: the safety engine is fed the user's stored clinical history,
    # otherwise the seeded scans would be blind to it.
    safety_ctx = build_history_context(db, user.id)
    run_analysis(db, session, safety_ctx)

    verdict = session.analysis.safety_verdict.verdict if session.analysis else "?"
    print(f"  scan {days_ago}d ago: analyzed (scalp_ratio={scalp_ratio}, safety={verdict})")
    return session


def _require_schema(db) -> None:
    """Seeding must not create tables itself.

    Using create_all() here would leave the database unstamped and drift out of
    sync with Alembic. Migrations own the schema; this script only adds rows.
    """
    from sqlalchemy import inspect

    if not inspect(db.get_bind()).has_table("users"):
        sys.exit("Schema not found. Run migrations first:\n    python -m alembic upgrade head")


def seed_history_and_shedding(db, user) -> None:
    """A plausible history that exercises the history-driven safety rules, plus
    90 days of shedding with a genuine downward trend on wash days."""
    if db.query(ClinicalHistory).filter(ClinicalHistory.user_id == user.id).count():
        return

    db.add(
        ClinicalHistory(
            user_id=user.id,
            onset="gradual",
            duration_months=18,
            pattern="crown",
            family_history_hair_loss=True,
            family_history_side="maternal",
            # A treatable systemic cause -> should raise 'caution', not a referral.
            iron_deficiency=True,
            major_stress=True,
            trigger_months_ago=14,
            medications=["levothyroxine 50mcg", "vitamin D"],
            heat_styling=True,
            notes="Noticed more hair in the shower drain since last winter.",
        )
    )

    rng = random.Random(7)
    for i in range(90):
        day = date.today() - timedelta(days=i)
        # Wash roughly every third day; brushing logged most days.
        if i % 3 == 0:
            # Gentle decline over time (older days = higher), plus daily noise.
            base = 70 + i * 0.7
            db.add(
                SheddingLog(
                    user_id=user.id, date=day, context="wash", washed_hair=True,
                    count=max(10, int(rng.gauss(base, 12))),
                )
            )
        elif i % 3 == 1:
            db.add(
                SheddingLog(
                    user_id=user.id, date=day, context="brush",
                    count=max(2, int(rng.gauss(14 + i * 0.1, 4))),
                )
            )
    db.commit()
    print("Clinical history + 90 days of shedding seeded")


def main() -> None:
    db = SessionLocal()
    try:
        _require_schema(db)
        ensure_evidence(db)
        user = ensure_user(db)
        print(f"Demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")

        # History FIRST: the safety engine reads it during analysis, so seeding it
        # afterwards would leave the demo scans blind to it.
        seed_history_and_shedding(db, user)

        # Three scans over ~3 months with slightly increasing scalp visibility.
        create_scan(db, user, days_ago=84, scalp_ratio=0.30, seed_base=1000)
        create_scan(db, user, days_ago=42, scalp_ratio=0.35, seed_base=2000)
        create_scan(db, user, days_ago=3, scalp_ratio=0.33, seed_base=3000)

        if not db.query(Treatment).filter(Treatment.user_id == user.id).count():
            t1 = Treatment(
                user_id=user.id, category="topical", name="Topical minoxidil 5% (OTC)",
                dose="1 mL", frequency="twice daily", start_date=date.today() - timedelta(days=70),
                is_prescribed_by_clinician=False,
            )
            t2 = Treatment(
                user_id=user.id, category="shampoo", name="Ketoconazole 1% shampoo",
                frequency="2x per week", start_date=date.today() - timedelta(days=45),
            )
            db.add_all([t1, t2])
            db.flush()
            rng = random.Random(42)
            for t, rate in ((t1, 0.86), (t2, 0.71)):
                for i in range(30):
                    db.add(AdherenceLog(treatment_id=t.id, date=date.today() - timedelta(days=i), taken=rng.random() < rate))
            db.commit()
            print("Treatments + 30 days of adherence seeded")

        print("\nDone. Start the API and sign in with the credentials above.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
