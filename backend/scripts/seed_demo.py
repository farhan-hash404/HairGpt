"""Seed a demo account with synthetic scans, treatments and adherence.

Generates SYNTHETIC images (procedurally drawn hair/scalp texture) purely so the
UI and pipeline can be exercised end-to-end. These are not real people and carry
no clinical meaning whatsoever.

Usage (backend venv active, server NOT required — talks to the DB directly):
    python -m scripts.seed_demo
"""

from __future__ import annotations

import math
import random
import sys
from datetime import date, timedelta
from io import BytesIO

from app.core.security import hash_password
from app.cv.registry import get_quality_gate
from app.cv.types import ImageInput
from app.db.session import SessionLocal, init_db
from app.models.scan import ImageQualityReport, ScanImage, ScanSession
from app.models.treatment import AdherenceLog, Treatment
from app.models.user import Consent, User
from app.rag.ingest import seed_corpus
from app.services.orchestrator import run_analysis
from app.services.storage import make_storage_key, storage

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demopassword123"
HAIR_VIEWS = ["front_hairline", "left_temple", "right_temple", "top", "crown", "sides", "back"]


def synth_scalp_image(seed: int, scalp_ratio: float, size: int = 1024) -> bytes:
    """Draw a synthetic scalp/hair texture: darker hair strands over lighter scalp.

    `scalp_ratio` (0..1) controls how much scalp shows through — this is what makes
    successive "scans" differ, so the timeline and comparison have real signal.
    """
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        sys.exit("Pillow is required for demo seeding: pip install Pillow")

    rng = random.Random(seed)
    img = Image.new("RGB", (size, size), (206, 178, 158))  # scalp base tone
    d = ImageDraw.Draw(img)

    # Vignette-ish lighting variation so exposure stats look natural.
    for y in range(0, size, 4):
        shade = int(12 * math.sin(y / size * math.pi))
        d.rectangle([0, y, size, y + 4], fill=(206 - shade, 178 - shade, 158 - shade))

    # Hair strands. Fewer strands => more visible scalp.
    n_strands = int(5200 * (1.0 - scalp_ratio))
    for _ in range(n_strands):
        x0 = rng.uniform(0, size)
        y0 = rng.uniform(0, size)
        length = rng.uniform(18, 46)
        angle = rng.uniform(-0.5, 0.5) + math.pi / 2
        x1 = x0 + math.cos(angle) * length
        y1 = y0 + math.sin(angle) * length
        tone = rng.randint(28, 74)
        d.line([(x0, y0), (x1, y1)], fill=(tone, tone - 6, tone - 10), width=rng.choice([1, 1, 2]))

    img = img.filter(ImageFilter.GaussianBlur(0.4))  # slight softness, still sharp enough
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
        print(f"  scan {days_ago}d ago: only {passed}/{len(HAIR_VIEWS)} views passed the quality gate — not analyzed")
        session.status = "rejected"
        db.commit()
        return None

    run_analysis(db, session)
    print(f"  scan {days_ago}d ago: analyzed (scalp_ratio={scalp_ratio})")
    return session


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_corpus(db)
        user = ensure_user(db)
        print(f"Demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")

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
