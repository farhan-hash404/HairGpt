# HairGPT — CV Abstraction Layer

**Goal:** no computer-vision architecture is hard-coded. Every capability is an interface (ABC) with (a) a **mock** implementation that ships by default and (b) a **real** implementation slot that loads a trained checkpoint. Swapping models is a config change, not a code change. Mock outputs are always flagged `is_mock=True` and `validated=False`.

## Interfaces (`backend/app/cv/base.py`)

```python
class ImageQualityGate(ABC):
    def assess(self, img: ImageInput, view: str, domain: str) -> ImageQualityReport: ...

class Segmenter(ABC):                 # hair / scalp / skin regions
    def segment(self, img, targets: list[str]) -> SegmentationResult: ...

class Localizer(ABC):                 # hairline / temple / crown landmarks
    def localize(self, img, seg: SegmentationResult, view: str) -> LocalizationResult: ...

class MetricEstimator(ABC):           # scalp visibility, apparent coverage/density
    def estimate(self, img, seg, loc) -> list[Observation]: ...

class FaceAnalyzer(ABC):              # SkinGPT: oiliness/redness/pigmentation/... 
    def analyze(self, img, view: str) -> list[Observation]: ...

class Aligner(ABC):                   # standardized alignment for longitudinal compare
    def align(self, img, view: str, reference: AlignmentRef | None) -> AlignmentResult: ...

class OCRExtractor(ABC):              # product label → text/ingredients
    def extract(self, img) -> OCRResult: ...
```

Shared value objects: `ConfidenceScore`, `Observation`, `SegmentationResult(masks, areas, confidence)`, `LocalizationResult(points, regions, confidence)`, `AlignmentResult(transform, quality)`.

## Registry & selection (`backend/app/cv/registry.py`)
A registry maps `(capability, backend)` → implementation. `CV_BACKEND=mock` (default) or `torch`. The rest of the app depends only on the ABCs via `get_quality_gate()`, `get_segmenter()`, etc. A `torch` backend that fails to load a checkpoint **falls back to mock and logs loudly** — it never silently degrades to a fake "real" result.

```
get_segmenter() ─► registry[("segmenter", CV_BACKEND)] ─► MockSegmenter | TorchSegmenter
```

## Mock implementations (`backend/app/cv/mock/`)
Deterministic (seeded by image hash) so demos and tests are reproducible. They use lightweight, honest heuristics — **not** trained models:
- **Quality:** variance-of-Laplacian proxy for blur, histogram stats for exposure/overexposure, face/edge size proxy for distance, symmetry proxy for angle, bright-pixel-in-parting proxy for scalp visibility. If OpenCV is absent, pure-NumPy fallbacks are used.
- **Segmentation:** color/luminance clustering to approximate hair vs scalp vs skin masks.
- **Localization:** region heuristics for hairline/temple/crown bounding areas.
- **Metrics:** scalp-visibility = scalp-mask area / head-region area; apparent density from texture density in the hair mask.
- **FaceAnalyzer:** channel/texture statistics mapped to oiliness/redness/pigmentation/pores/texture labels.
- **Aligner:** ORB/keypoint or centroid+scale normalization; returns an honest low `quality` when it cannot align.
- **OCR:** if `pytesseract` present, real OCR; else returns `confidence=0` and asks for manual entry.

Every mock result: `is_mock=True`, `validated=False`, `model_version="mock-*@0.x"`.

## Real implementation slot (`backend/app/cv/torch/`)
`TorchSegmenter`, `TorchFaceAnalyzer`, etc. load checkpoints from `CV_MODEL_DIR`. Suggested production choices (interchangeable):
- Hair/scalp segmentation: a U-Net / SegFormer / DeepLabv3+ head fine-tuned on scalp datasets.
- Face landmarks: MediaPipe FaceMesh or a HRNet landmark model (used for alignment & region cropping only — **not** identity).
- Skin attributes: multi-head CNN/ViT regressors per attribute, each emitting calibrated confidence.
Checkpoints are versioned; `model_version` is recorded on every observation for provenance and reproducibility. **No mock is ever labeled validated**, and promotion to `validated=True` requires the stratified evaluation in [`08-roadmap.md`](08-roadmap.md).

## Confidence & calibration
Each estimator returns a `ConfidenceScore` with `basis` (what drove it) and `method` (id). The pipeline computes overall confidence as a conservative aggregate (≈ min of required stages, penalized by quality). Real models must ship a calibration curve (reliability diagram) before `validated=True`.

## Why images don't go straight to the LLM
CV services convert pixels → **structured, typed observations**. Only that JSON (plus retrieved evidence and the safety verdict) reaches the LLM. This keeps the diagnostic-relevant computation deterministic, testable, auditable, and swappable — and prevents an LLM from hallucinating measurements from raw pixels.
