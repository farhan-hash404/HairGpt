"""Regression tests for image decoding.

Bug once fixed here: DecodedImage downscaled to a 256x256 analysis thumbnail and
then reported the THUMBNAIL size as the image dimensions, so the distance /
resolution-adequacy proxy judged every photo as too far away.
"""
from __future__ import annotations

from io import BytesIO

import pytest

from app.cv.imageio import HAS_PIXELS, DecodedImage

pytestmark = pytest.mark.skipif(not HAS_PIXELS, reason="numpy/Pillow not installed")


def _jpeg(size: int) -> bytes:
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (size, size), (180, 150, 130)).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_dimensions_reflect_original_not_thumbnail():
    data = _jpeg(1024)
    d = DecodedImage(data)
    assert (d.width, d.height) == (1024, 1024)
    # The analysis buffer is still downscaled for speed.
    assert d.gray is not None and max(d.gray.shape) <= 256


def test_size_proxy_scales_with_original_resolution():
    small = DecodedImage(_jpeg(200)).size_proxy()
    large = DecodedImage(_jpeg(1024)).size_proxy()
    assert small < large
    assert large == pytest.approx(1.0)  # 1024x1024 exceeds the useful-detail floor


def test_adequate_resolution_passes_distance_check():
    from app.cv.mock.quality import MockImageQualityGate
    from app.cv.types import ImageInput

    report = MockImageQualityGate().assess(ImageInput(data=_jpeg(1024)), "front_hairline", "hair")
    assert report.distance_ok is True
    assert "incorrect_distance" not in report.reasons
