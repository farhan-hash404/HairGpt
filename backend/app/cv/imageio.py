from __future__ import annotations

import hashlib
import io
import struct

# Optional scientific stack. When absent, we degrade to a deterministic,
# hash-seeded pseudo-analysis that is CLEARLY still labeled mock/low-confidence.
try:  # pragma: no cover - environment dependent
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None

try:  # pragma: no cover
    from PIL import Image as _PILImage
except Exception:  # pragma: no cover
    _PILImage = None

HAS_PIXELS = _np is not None and _PILImage is not None


def _seed_floats(data: bytes, n: int) -> list[float]:
    """Deterministic pseudo-random floats in [0,1) seeded by the image bytes."""
    out: list[float] = []
    h = hashlib.sha256(data).digest()
    i = 0
    while len(out) < n:
        if i + 4 > len(h):
            h = hashlib.sha256(h).digest()
            i = 0
        (v,) = struct.unpack_from(">I", h, i)
        out.append((v % 100000) / 100000.0)
        i += 4
    return out


def _dims_from_bytes(data: bytes) -> tuple[int, int]:
    """Best-effort dimension sniff for JPEG/PNG without a full decoder."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", data[16:24])
            return int(w), int(h)
        if data[:2] == b"\xff\xd8":  # JPEG: scan SOF markers
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                    h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                    return int(w), int(h)
                seg_len = struct.unpack(">H", data[i + 2 : i + 4])[0]
                i += 2 + seg_len
    except Exception:
        pass
    return 0, 0


class DecodedImage:
    """Uniform interface over real-pixel and pseudo-metric modes."""

    def __init__(self, data: bytes):
        self.data = data
        self._pseudo = _seed_floats(data, 8)
        self.gray = None
        # Original capture dimensions, kept separate from the analysis thumbnail:
        # the distance/size proxy must reflect the real photo, not the downscale.
        self.width, self.height = _dims_from_bytes(data)
        if HAS_PIXELS:
            try:
                im = _PILImage.open(io.BytesIO(data)).convert("L")
                self.width, self.height = im.size
                # Downscale for speed; the texture heuristics are scale-tolerant.
                im.thumbnail((256, 256))
                self.gray = _np.asarray(im, dtype="float32")
            except Exception:
                self.gray = None

    @property
    def real_pixels(self) -> bool:
        return self.gray is not None

    # --- Heuristic metrics (real when pixels available, else deterministic pseudo) ---

    def blur_score(self) -> float:
        """0 = very blurry, 1 = sharp. Variance-of-Laplacian proxy."""
        if not self.real_pixels:
            return 0.35 + 0.5 * self._pseudo[0]
        g = self.gray
        lap = (
            -4 * g[1:-1, 1:-1]
            + g[:-2, 1:-1]
            + g[2:, 1:-1]
            + g[1:-1, :-2]
            + g[1:-1, 2:]
        )
        var = float(lap.var())
        # Map variance to 0..1 with a soft knee (~100 = borderline sharp).
        return max(0.0, min(1.0, var / (var + 120.0)))

    def mean_brightness(self) -> float:
        if not self.real_pixels:
            return 0.3 + 0.5 * self._pseudo[1]
        return float(self.gray.mean()) / 255.0

    def overexposed_fraction(self) -> float:
        if not self.real_pixels:
            return 0.02 + 0.15 * self._pseudo[2]
        return float((self.gray > 245).mean())

    def symmetry(self) -> float:
        """1 = left/right symmetric (well-framed), 0 = strongly asymmetric (bad angle)."""
        if not self.real_pixels:
            return 0.55 + 0.4 * self._pseudo[3]
        g = self.gray
        flipped = g[:, ::-1]
        diff = float((g - flipped).__abs__().mean()) / 255.0
        return max(0.0, min(1.0, 1.0 - diff))

    def bright_parting_fraction(self) -> float:
        """Proxy for scalp visibility: fraction of bright pixels along vertical bands."""
        if not self.real_pixels:
            return 0.1 + 0.35 * self._pseudo[4]
        g = self.gray
        # Scalp shows as brighter skin among darker hair.
        thresh = g.mean() + 0.6 * g.std()
        return float((g > thresh).mean())

    # Reference resolution below which detail is too coarse to assess a scalp
    # region reliably. ~800x800 of actual subject area.
    _MIN_USEFUL_PX = 800.0 * 800.0

    def size_proxy(self) -> float:
        """Resolution-adequacy proxy standing in for 'subject fills the frame'.

        HONEST LIMITATION: true distance estimation needs a head/face landmark
        model to measure subject size relative to the frame. Until the real
        backend is wired in, we can only verify there is enough pixel detail to
        analyze. A high-resolution photo taken from far away will pass this check.
        """
        px = float(self.width * self.height)
        if not px:
            return 0.4 + 0.4 * self._pseudo[5]
        return min(1.0, px / self._MIN_USEFUL_PX)
