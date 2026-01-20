from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .fs import make_output_path
from .models import BatchResult, JobSpec
from .optimizer import save_with_optimization, strip_metadata
from .thumbnailer import apply_overlay, apply_studio_overlay, draw_number, open_image, resize_to_spec


def _resolve_output_extension(output_format: str, source_path: Path) -> str:
    fmt = output_format.lower()
    if fmt == "keep":
        return source_path.suffix.lstrip(".")
    return fmt


def process_files(input_paths: list[Path], output_dir: Path, spec: JobSpec) -> BatchResult:
    failures: list[str] = []
    saved = 0
    output_files: list[str] = []

    for idx, path in enumerate(input_paths, start=1):
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

                # Save with conversions appropriate for the effective format.
                no_opt = replace(spec.optimize, enabled=False)
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

            saved += 1
            output_files.append(str(out_path))
            if warning:
                failures.append(f"{path}: {warning}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{path}: {exc}")

    return BatchResult(processed=len(input_paths), saved=saved, failures=failures, output_files=output_files)
