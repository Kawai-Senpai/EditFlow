"""Thumbnail generation utilities for EditFlow."""

from .models import (
    ResizeSpec,
    OverlaySpec,
    NumberingSpec,
    OptimizeSpec,
    JobSpec,
    BatchResult,
    StudioOverlaySpec,
)
from .thumbnailer import open_image, resize_to_spec, apply_overlay, apply_studio_overlay, draw_number
from .optimizer import save_with_optimization, strip_metadata
from .batch import process_files

__all__ = [
    "ResizeSpec",
    "OverlaySpec",
    "NumberingSpec",
    "OptimizeSpec",
    "JobSpec",
    "BatchResult",
    "StudioOverlaySpec",
    "open_image",
    "resize_to_spec",
    "apply_overlay",
    "apply_studio_overlay",
    "draw_number",
    "save_with_optimization",
    "strip_metadata",
    "process_files",
]
