"""Capture-consistency (ghost overlay) behaviour.

Framing is a WARNING, never a blocker: refusing a scan is worse for a tracking
product than accepting a flagged one. The score instead gates comparison
confidence downstream.

The property that matters most: the metric must respond to how the photo was
FRAMED without responding to the hair change we are actually trying to measure.
"""
from __future__ import annotations

import pytest

from app.cv.imageio import HAS_PIXELS
from app.services.framing import (
    FRAMING_WARN_THRESHOLD,
    _layout_signature,
    _layout_similarity,
    compute_framing_match,
)

pytestmark = pytest.mark.skipif(not HAS_PIXELS, reason="numpy/Pillow not installed")


def _img(**kwargs) -> bytes:
    from scripts.seed_demo import synth_scalp_image

    kwargs.setdefault("seed", 4200)
    kwargs.setdefault("scalp_ratio", 0.32)
    return synth_scalp_image(**kwargs)


def _match(reference: bytes, candidate: bytes) -> float:
    a, b = _layout_signature(reference), _layout_signature(candidate)
    assert a is not None and b is not None
    return _layout_similarity(a, b)


# --- applicability ---------------------------------------------------------

def test_no_reference_yields_none_not_a_failure():
    """A first scan has nothing to compare against — None, never 0.0."""
    assert compute_framing_match(db=None, reference=None, view="crown", data=_img()) is None


def test_flat_frame_has_no_layout_information():
    """A featureless frame cannot support a framing judgement, so we say so."""
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (512, 512), (128, 128, 128)).save(buf, format="JPEG", quality=95)
    assert _layout_signature(buf.getvalue()) is None


# --- discrimination --------------------------------------------------------

def test_same_framing_scores_near_perfect():
    assert _match(_img(seed=1), _img(seed=2)) > 0.9


def test_horizontal_shift_is_flagged():
    score = _match(_img(), _img(offset=(0.12, 0.0)))
    assert score < FRAMING_WARN_THRESHOLD, f"a 12% lateral shift should warn (got {score})"


def test_zoom_change_is_flagged():
    score = _match(_img(), _img(zoom=0.65))
    assert score < FRAMING_WARN_THRESHOLD, f"a 35% zoom-out should warn (got {score})"


def test_metric_ignores_the_change_it_is_meant_to_survive():
    """A real change in hair density must NOT read as a framing problem.

    If it did, the metric would penalise exactly the signal the product exists to
    detect, and users would be told to retake good photos of genuine change.
    """
    same_framing_more_scalp = _match(_img(scalp_ratio=0.30), _img(scalp_ratio=0.55))
    assert same_framing_more_scalp > 0.9


def test_framing_beats_density_as_an_explanation_of_difference():
    """Framing change must move the score far more than density change does."""
    density_effect = 1.0 - _match(_img(scalp_ratio=0.30), _img(scalp_ratio=0.55))
    framing_effect = 1.0 - _match(_img(), _img(offset=(0.12, 0.0)))
    assert framing_effect > density_effect * 3


# --- integration -----------------------------------------------------------

def test_poor_framing_warns_but_never_blocks_upload(client_with_reference):
    client, headers, _ = client_with_reference
    sid = client.post("/api/v1/scans", json={"domain": "hair"}, headers=headers).json()["session_id"]
    r = client.post(
        f"/api/v1/scans/{sid}/images/upload",
        data={"view": "crown"},
        files={"file": ("x.jpg", _img(offset=(0.2, 0.1)), "image/jpeg")},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert "framing_match" in body
    # Whatever the score, a framing problem must never be a rejection reason.
    assert "framing" not in " ".join(body["reasons"]).lower()


def test_first_scan_reports_no_reference(client):
    from tests.conftest import authenticate, grant_consent

    headers = authenticate(client, "firstscan@example.com")
    grant_consent(client, headers)
    assert client.get("/api/v1/scans/reference?domain=hair", headers=headers).json()["reference"] is None


def test_reference_appears_after_a_completed_scan(client_with_reference):
    client, headers, reference_sid = client_with_reference
    ref = client.get("/api/v1/scans/reference?domain=hair", headers=headers).json()["reference"]
    assert ref is not None
    assert ref["session_id"] == reference_sid
    assert len(ref["views"]) == 7  # every view passed quality in the fixture
