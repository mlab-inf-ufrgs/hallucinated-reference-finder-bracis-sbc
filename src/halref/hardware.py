"""Local accelerator detection for optional ML extractors (Marker, Docling).

The default halref path (pdfminer, pypdf, pdfplumber, HTTP APIs) is CPU- and
network-bound; this module only affects optional ``marker`` / ``docling``
extractors when installed.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

logger = logging.getLogger(__name__)

TorchDeviceName = Literal["cuda", "mps", "cpu"]


def detect_torch_device() -> TorchDeviceName:
    """Pick the best available torch device, or CPU if torch is missing or no GPU."""
    try:
        import torch
    except ImportError:
        return "cpu"
    try:
        if torch.cuda.is_available():
            return "cuda"
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            return "mps"
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("torch device probe failed: %s", exc)
    return "cpu"


def ensure_inference_device_env(*, prefer_gpu: bool = True) -> TorchDeviceName:
    """Set ``TORCH_DEVICE`` and ``DOCLING_DEVICE`` when unset (Marker / Docling).

    Existing environment values are never overwritten, so users can force
    ``TORCH_DEVICE=cpu`` etc. When ``prefer_gpu`` is false, defaults both to CPU.
    """
    if not prefer_gpu:
        os.environ.setdefault("TORCH_DEVICE", "cpu")
        os.environ.setdefault("DOCLING_DEVICE", "cpu")
        return "cpu"

    dev: TorchDeviceName = detect_torch_device()
    os.environ.setdefault("TORCH_DEVICE", dev)
    os.environ.setdefault("DOCLING_DEVICE", dev)
    if dev != "cpu":
        logger.info(
            "ML extractors: using %s (set TORCH_DEVICE/DOCLING_DEVICE in env to override)",
            dev,
        )
    return dev


def create_marker_model_dict():
    """Build Marker's model dict, passing ``device=`` when supported."""
    from marker.models import create_model_dict

    dev = os.environ.get("TORCH_DEVICE") or detect_torch_device()
    if dev == "cpu":
        return create_model_dict()
    try:
        return create_model_dict(device=dev)
    except TypeError:
        return create_model_dict()
