"""Real (trained-model) CV backend slot.

This module is intentionally a stub in the MVP. Wire real checkpoints here — each
must implement the matching ABC from `app.cv.base` and set `is_mock=False` /
`validated=True` ONLY after passing the stratified evaluation in docs/08-roadmap.md.

Example (production):

    from app.cv.torch.segmenter import TorchSegmenter
    def get(capability, model_dir):
        if capability == "segmenter":
            return TorchSegmenter(model_dir)
        ...
        return None

Returning None for a capability makes the registry fall back to mock and log loudly.
"""

from __future__ import annotations


def get(capability: str, model_dir: str):  # noqa: ARG001
    # No trained checkpoints ship with the MVP. Real models plug in here.
    return None
