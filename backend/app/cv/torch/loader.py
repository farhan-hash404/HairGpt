from __future__ import annotations

import logging
from pathlib import Path

from app.cv.manifest import ModelSpec

log = logging.getLogger("hairgpt.cv.torch")


class CheckpointUnavailable(RuntimeError):
    """Raised when a real model cannot be loaded. The registry catches this and
    falls back to mock — loudly. We never substitute silently."""


def require_torch():
    try:
        import torch  # noqa: F401

        return torch
    except ImportError as exc:  # pragma: no cover - depends on optional stack
        raise CheckpointUnavailable(
            "PyTorch is not installed. Install it, or set CV_BACKEND=mock."
        ) from exc


def load_checkpoint(spec: ModelSpec, model_dir: str):
    """Load a TorchScript module or a state_dict-backed model from the manifest.

    TorchScript is preferred because it carries its own architecture — a plain
    state_dict requires the exact model class to be reconstructed here, which is
    a common source of silent mismatch.
    """
    torch = require_torch()
    path = Path(model_dir) / spec.checkpoint
    if not path.exists():
        raise CheckpointUnavailable(f"checkpoint not found: {path}")

    try:
        module = torch.jit.load(str(path), map_location="cpu")
        module.eval()
        log.info("loaded TorchScript model %s@%s", spec.name, spec.version)
        return module
    except Exception:
        pass  # not TorchScript; try a state_dict below

    try:
        state = torch.load(str(path), map_location="cpu", weights_only=True)
    except Exception as exc:
        raise CheckpointUnavailable(f"could not read checkpoint {path}: {exc}") from exc

    builder = _ARCHITECTURES.get(spec.architecture)
    if builder is None:
        raise CheckpointUnavailable(
            f"checkpoint {path} is a state_dict but architecture "
            f"'{spec.architecture}' is not registered. Export it as TorchScript, "
            f"or register a builder in app/cv/torch/loader.py."
        )
    model = builder(spec)
    model.load_state_dict(state)
    model.eval()
    log.info("loaded %s model %s@%s", spec.architecture, spec.name, spec.version)
    return model


# Architecture builders for state_dict checkpoints. Register real classes here
# as they are introduced; TorchScript export avoids needing this entirely.
_ARCHITECTURES: dict[str, callable] = {}


def register_architecture(name: str):
    def decorator(builder):
        _ARCHITECTURES[name] = builder
        return builder

    return decorator


def preprocess(image_bytes: bytes, size: int):
    """Bytes -> normalized CHW float tensor, using ImageNet statistics."""
    torch = require_torch()
    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        raise CheckpointUnavailable("numpy and Pillow are required for real inference") from exc

    import io

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((size, size))
    array = np.asarray(image, dtype="float32") / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype="float32")
    std = np.array([0.229, 0.224, 0.225], dtype="float32")
    array = (array - mean) / std
    return torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
