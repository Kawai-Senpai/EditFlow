from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from .models import OptimizeSpec
from .util import parse_hex_color


def strip_metadata(img: Image.Image) -> Image.Image:
    # Create a new image to drop metadata/EXIF/text chunks.
    if img.mode == "P":
        img = img.convert("RGBA")
    clean = Image.new(img.mode, img.size)
    clean.putdata(img.getdata())
    return clean


def _flatten_for_jpeg(img: Image.Image, background_hex: str) -> Image.Image:
    if img.mode in {"RGBA", "LA"}:
        bg = Image.new("RGBA", img.size, parse_hex_color(background_hex) + (255,))
        bg.paste(img, (0, 0), img)
        return bg.convert("RGB")
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _encode_jpeg_to_bytes(img: Image.Image, quality: int) -> bytes:
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def save_with_optimization(
    img: Image.Image,
    dest_path: Path,
    output_format: str,
    optimize_spec: OptimizeSpec,
    background_for_flatten: str,
) -> tuple[Path, str | None]:
    """Save image, optionally enforcing a max file size.

    Returns: (final_path, warning_message)
    """
    fmt = output_format.lower()

    # If asked to optimize size, prefer JPEG for predictable max-bytes.
    if optimize_spec.enabled and optimize_spec.allow_format_change_to_jpeg and fmt in {"png", "webp"}:
        fmt = "jpeg"

    if fmt == "jpeg":
        rgb = _flatten_for_jpeg(img, background_for_flatten)
        if not optimize_spec.enabled:
            rgb.save(dest_path, format="JPEG", quality=optimize_spec.jpeg_quality_start, optimize=True, progressive=True)
            return dest_path, None

        quality = optimize_spec.jpeg_quality_start
        min_q = optimize_spec.jpeg_quality_min
        current = rgb

        for _ in range(30):
            while quality >= min_q:
                data = _encode_jpeg_to_bytes(current, quality)
                if len(data) <= optimize_spec.max_bytes:
                    dest_path.write_bytes(data)
                    return dest_path, None
                quality -= 5

            # Still too big: downscale slightly and try again.
            quality = optimize_spec.jpeg_quality_start
            new_w = max(64, int(current.width * 0.95))
            new_h = max(64, int(current.height * 0.95))
            if new_w == current.width and new_h == current.height:
                break
            current = current.resize((new_w, new_h), resample=Image.LANCZOS)

        # Fallback: write best effort at min quality.
        data = _encode_jpeg_to_bytes(current, min_q)
        dest_path.write_bytes(data)
        return dest_path, f"Could not hit max_bytes={optimize_spec.max_bytes}; saved best-effort ({len(data)} bytes)."

    if fmt == "png":
        save_kwargs = {"optimize": True, "compress_level": 9}
        img.save(dest_path, format="PNG", **save_kwargs)
        if optimize_spec.enabled and dest_path.stat().st_size > optimize_spec.max_bytes:
            return dest_path, (
                f"PNG may exceed max_bytes={optimize_spec.max_bytes}. "
                "Consider output_format=jpeg for reliable size limits."
            )
        return dest_path, None

    if fmt == "webp":
        # WebP can be great for size, but support varies by usage.
        quality = 90
        img.save(dest_path, format="WEBP", quality=quality, method=6)
        if optimize_spec.enabled and dest_path.stat().st_size > optimize_spec.max_bytes:
            return dest_path, (
                f"WEBP exceeded max_bytes={optimize_spec.max_bytes}. "
                "Consider output_format=jpeg or a lower quality."
            )
        return dest_path, None

    raise ValueError(f"Unsupported output_format: {output_format}")
