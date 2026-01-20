from __future__ import annotations

from pathlib import Path


DEFAULT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def iter_image_files(root: Path, recursive: bool, extensions: set[str] | None = None) -> list[Path]:
    exts = {e.lower() for e in (extensions or DEFAULT_EXTENSIONS)}
    pattern = "**/*" if recursive else "*"
    files = [p for p in root.glob(pattern) if p.is_file() and p.suffix.lower() in exts]
    files.sort(key=lambda p: str(p).lower())
    return files


def _sanitize_stem(stem: str) -> str:
    cleaned = "".join(ch for ch in stem if ch.isalnum() or ch in {"-", "_"})
    return cleaned or "image"


def make_output_path(
    input_path: Path,
    output_root: Path,
    suffix: str,
    output_ext: str,
    name_override: str | None = None,
) -> Path:
    base_name = _sanitize_stem(name_override or input_path.stem)
    ext = output_ext if output_ext.startswith(".") else f".{output_ext}"

    candidate = output_root / f"{base_name}{suffix}{ext}"
    if not candidate.exists():
        return candidate

    for i in range(1, 1000):
        candidate = output_root / f"{base_name}{suffix}_{i}{ext}"
        if not candidate.exists():
            return candidate

    return output_root / f"{base_name}{suffix}_{Path(input_path).stem[:6]}{ext}"
