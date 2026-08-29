"""Real (trained-model) CV backend.

Enabled with `CV_BACKEND=torch`. Models are declared in
`<CV_MODEL_DIR>/manifest.json`; see `models/manifest.example.json`.

Three rules govern this package:

1. A capability with no manifest entry, no checkpoint, or no PyTorch returns
   None, and the registry falls back to mock **with a loud warning**. Silent
   substitution of a heuristic for a trained model is never acceptable here.
2. A real model that has not passed the stratified evaluation still runs, but
   reports `validated=False` and has its confidence capped. It is a real model,
   not a trusted one.
3. Nothing in this package may set `validated=True` on its own — that flag comes
   only from a passing evaluation record, re-derived from the recorded metrics
   on every load (see `app.cv.manifest.validation_passes`).
"""

from __future__ import annotations

import logging

from app.cv.manifest import load_manifest
from app.cv.torch.loader import CheckpointUnavailable

log = logging.getLogger("hairgpt.cv.torch")

_BUILDERS = {
    "segmenter": ("app.cv.torch.segmenter", "TorchSegmenter"),
    "face": ("app.cv.torch.face", "TorchFaceAnalyzer"),
}


def get(capability: str, model_dir: str):
    """Return a real implementation, or None to fall back to mock."""
    specs = load_manifest(model_dir)
    spec = specs.get(capability)
    if spec is None:
        log.info("CV[%s]: no manifest entry; falling back to mock", capability)
        return None

    target = _BUILDERS.get(capability)
    if target is None:
        log.info(
            "CV[%s]: declared in the manifest but no torch implementation exists yet; "
            "falling back to mock",
            capability,
        )
        return None

    module_path, class_name = target
    try:
        import importlib

        cls = getattr(importlib.import_module(module_path), class_name)
        instance = cls(spec, model_dir)
    except CheckpointUnavailable as exc:
        log.warning("CV[%s]: %s -> FALLING BACK TO MOCK", capability, exc)
        return None
    except Exception as exc:  # pragma: no cover - depends on optional stack
        log.warning("CV[%s]: failed to build (%s) -> FALLING BACK TO MOCK", capability, exc)
        return None

    if not spec.is_validated:
        log.warning(
            "CV[%s]: running REAL model %s@%s which is NOT VALIDATED. Output will be "
            "labelled unvalidated and its confidence capped.",
            capability, spec.name, spec.version,
        )
    return instance
