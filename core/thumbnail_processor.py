"""Thumbnail processor - handles thumbnail generation jobs."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .thumbnail_generator.batch import _resolve_output_extension
from .thumbnail_generator.fs import make_output_path
from .thumbnail_generator.models import JobSpec, NumberingSpec, OptimizeSpec, OverlaySpec, ResizeSpec, StudioOverlaySpec
from .thumbnail_generator.optimizer import save_with_optimization, strip_metadata
from .thumbnail_generator.thumbnailer import apply_overlay, apply_studio_overlay, draw_number, open_image, resize_to_spec


@dataclass
class ThumbnailJob:
    id: str
    status: str = "pending"  # pending, processing, completed, failed, cancelled
    progress: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    current_step_num: int = 0
    output_files: list = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    error: Optional[str] = None
    cancelled: bool = False


class ThumbnailProcessor:
    """Handles thumbnail processing operations."""

    def __init__(self):
        self.jobs: dict[str, ThumbnailJob] = {}

    def create_job(self) -> ThumbnailJob:
        job_id = str(uuid.uuid4())[:8].upper()
        job = ThumbnailJob(id=job_id)
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[ThumbnailJob]:
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job and job.status == "processing":
            job.cancelled = True
            job.status = "cancelled"
            return True
        return False

    def build_job_spec(self, payload: dict) -> JobSpec:
        resize_payload = payload.get("resize") or {}
        resize = None
        if resize_payload:
            resize = ResizeSpec(
                width=int(resize_payload.get("width", 1280)),
                height=int(resize_payload.get("height", 720)),
                fit_mode=resize_payload.get("fit_mode", "cover"),
                background=resize_payload.get("background", "#000000"),
            )

        overlay = None
        studio_overlay = None
        overlay_payload = payload.get("overlay") or {}
        overlay_type = overlay_payload.get("type", "none")
        if overlay_type == "image":
            overlay = OverlaySpec(
                path=Path(overlay_payload.get("path")),
                mode=overlay_payload.get("mode", "scale_to_canvas"),
                opacity=float(overlay_payload.get("opacity", 1.0)),
            )
        elif overlay_type == "studio":
            studio_data = overlay_payload.get("studio") or {}
            studio_overlay = StudioOverlaySpec(
                width=int(studio_data.get("width", resize.width if resize else 1280)),
                height=int(studio_data.get("height", resize.height if resize else 720)),
                elements=list(studio_data.get("elements", [])),
            )

        numbering_payload = payload.get("numbering") or {}
        numbering = NumberingSpec(
            enabled=bool(numbering_payload.get("enabled", False)),
            start=int(numbering_payload.get("start", 1)),
            position=numbering_payload.get("position", "bottom-right"),
            margin=int(numbering_payload.get("margin", 24)),
            font_size=int(numbering_payload.get("font_size", 0)),
            line_height=float(numbering_payload.get("line_height", 1.1)),
            letter_spacing=float(numbering_payload.get("letter_spacing", 0)),
            fill=numbering_payload.get("fill", "#ffffff"),
            fill_enabled=bool(numbering_payload.get("fill_enabled", True)),
            stroke_fill=numbering_payload.get("stroke_fill", "#000000"),
            stroke_width=int(numbering_payload.get("stroke_width", 4)),
            stroke_enabled=bool(numbering_payload.get("stroke_enabled", True)),
            font_path=Path(numbering_payload["font_path"]) if numbering_payload.get("font_path") else None,
            x=int(numbering_payload["x"]) if numbering_payload.get("x") is not None else None,
            y=int(numbering_payload["y"]) if numbering_payload.get("y") is not None else None,
        )

        optimize_payload = payload.get("optimize") or {}
        optimize = OptimizeSpec(
            enabled=bool(optimize_payload.get("enabled", True)),
            max_bytes=int(optimize_payload.get("max_bytes", 2 * 1024 * 1024)),
            jpeg_quality_start=int(optimize_payload.get("jpeg_quality_start", 92)),
            jpeg_quality_min=int(optimize_payload.get("jpeg_quality_min", 30)),
            allow_format_change_to_jpeg=bool(optimize_payload.get("allow_format_change_to_jpeg", True)),
        )

        return JobSpec(
            output_format=payload.get("output_format", "jpeg"),
            resize=resize,
            overlay=overlay,
            studio_overlay=studio_overlay,
            numbering=numbering,
            optimize=optimize,
            strip_metadata=bool(payload.get("strip_metadata", True)),
            filename_suffix=payload.get("filename_suffix", "_thumb"),
            background_for_flatten=payload.get("background_for_flatten", "#000000"),
        )

    def process_thumbnails(self, job: ThumbnailJob, backgrounds: list[dict], output_dir: Path, spec: JobSpec):
        job.status = "processing"
        job.total_steps = len(backgrounds)
        job.current_step_num = 0
        job.progress = 0

        if not backgrounds:
            job.status = "failed"
            job.error = "No backgrounds provided"
            return

        for idx, item in enumerate(backgrounds, start=1):
            if job.cancelled:
                job.status = "cancelled"
                return

            path_raw = item.get("path")
            name_override = item.get("name")
            if not path_raw:
                job.failures.append("Missing background path")
                continue

            path = Path(path_raw)
            if not path.exists():
                job.failures.append(f"Background not found: {path}")
                continue

            job.current_step_num = idx
            job.current_step = f"Rendering {idx}/{job.total_steps}: {path.name}"
            job.progress = (idx - 1) / max(1, job.total_steps) * 100

            try:
                img = open_image(path)

                needs_rgba = spec.resize is not None or spec.overlay is not None or spec.studio_overlay is not None or spec.numbering.enabled
                if spec.resize is not None:
                    img = resize_to_spec(img, spec.resize)
                elif needs_rgba:
                    img = img.convert("RGBA")

                if spec.overlay is not None:
                    img = apply_overlay(img, spec.overlay)
                if spec.studio_overlay is not None:
                    img = apply_studio_overlay(img, spec.studio_overlay.__dict__)

                if spec.numbering.enabled:
                    img = draw_number(img, spec.numbering.start + (idx - 1), spec.numbering)

                if spec.strip_metadata:
                    img = strip_metadata(img)

                out_ext = _resolve_output_extension(spec.output_format, path)
                out_path = make_output_path(
                    input_path=path,
                    output_root=output_dir,
                    suffix=spec.filename_suffix,
                    output_ext=out_ext,
                    name_override=name_override,
                )

                warning = None
                if spec.output_format.lower() == "keep":
                    ext = path.suffix.lower()
                    if ext in {".jpg", ".jpeg"}:
                        effective_fmt = "jpeg"
                    elif ext == ".png":
                        effective_fmt = "png"
                    elif ext == ".webp":
                        effective_fmt = "webp"
                    else:
                        effective_fmt = "png"

                    no_opt = OptimizeSpec(
                        enabled=False,
                        max_bytes=spec.optimize.max_bytes,
                        jpeg_quality_start=spec.optimize.jpeg_quality_start,
                        jpeg_quality_min=spec.optimize.jpeg_quality_min,
                        allow_format_change_to_jpeg=False,
                    )
                    _, warning = save_with_optimization(
                        img,
                        out_path,
                        effective_fmt,
                        no_opt,
                        background_for_flatten=spec.background_for_flatten,
                    )
                else:
                    _, warning = save_with_optimization(
                        img,
                        out_path,
                        spec.output_format,
                        spec.optimize,
                        background_for_flatten=spec.background_for_flatten,
                    )

                job.output_files.append(str(out_path))
                if warning:
                    job.failures.append(f"{path}: {warning}")
            except Exception as exc:  # noqa: BLE001
                job.failures.append(f"{path}: {exc}")

            job.progress = idx / max(1, job.total_steps) * 100

        if job.status != "cancelled":
            job.status = "completed"
            job.progress = 100


thumbnail_processor = ThumbnailProcessor()
