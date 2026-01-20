from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResizeSpec:
    width: int
    height: int
    fit_mode: str = "cover"  # cover | contain
    background: str = "#000000"


@dataclass(frozen=True)
class OverlaySpec:
    path: Path
    mode: str = "scale_to_canvas"  # scale_to_canvas | fit_width | fit_height | center_original
    opacity: float = 1.0


@dataclass(frozen=True)
class NumberingSpec:
    enabled: bool = False
    start: int = 1
    position: str = "bottom-right"  # top-left | top-right | bottom-left | bottom-right | center
    margin: int = 24
    font_size: int = 0  # 0 = auto
    line_height: float = 1.1
    letter_spacing: float = 0.0
    fill: str = "#ffffff"
    fill_enabled: bool = True
    stroke_fill: str = "#000000"
    stroke_width: int = 4
    stroke_enabled: bool = True
    font_path: Path | None = None
    x: int | None = None
    y: int | None = None


@dataclass(frozen=True)
class OptimizeSpec:
    enabled: bool = True
    max_bytes: int = 2 * 1024 * 1024
    jpeg_quality_start: int = 92
    jpeg_quality_min: int = 30
    allow_format_change_to_jpeg: bool = True


@dataclass(frozen=True)
class StudioOverlaySpec:
    width: int
    height: int
    elements: list[dict[str, Any]]


@dataclass(frozen=True)
class JobSpec:
    output_format: str = "jpeg"  # jpeg | png | webp | keep (metadata-only mode)
    resize: ResizeSpec | None = None
    overlay: OverlaySpec | None = None
    studio_overlay: StudioOverlaySpec | None = None
    numbering: NumberingSpec = NumberingSpec(enabled=False)
    optimize: OptimizeSpec = OptimizeSpec(enabled=True)
    strip_metadata: bool = True
    filename_suffix: str = "_thumb"
    background_for_flatten: str = "#000000"


@dataclass(frozen=True)
class BatchResult:
    processed: int
    saved: int
    failures: list[str]
    output_files: list[str]
