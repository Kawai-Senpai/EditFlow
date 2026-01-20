from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .models import NumberingSpec, OverlaySpec, ResizeSpec
from .studio import render_studio_overlay
from .util import clamp, parse_hex_color


def open_image(path: Path) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img


def resize_to_spec(img: Image.Image, spec: ResizeSpec) -> Image.Image:
    target_size = (spec.width, spec.height)
    if spec.fit_mode == "contain":
        contained = ImageOps.contain(img, target_size, method=Image.LANCZOS)
        bg = Image.new("RGBA", target_size, parse_hex_color(spec.background) + (255,))
        offset = ((spec.width - contained.width) // 2, (spec.height - contained.height) // 2)
        bg.paste(contained.convert("RGBA"), offset, contained.convert("RGBA"))
        return bg

    # default: cover
    fitted = ImageOps.fit(img, target_size, method=Image.LANCZOS, centering=(0.5, 0.5))
    return fitted.convert("RGBA")


def _apply_opacity(overlay: Image.Image, opacity: float) -> Image.Image:
    opacity = clamp(opacity, 0.0, 1.0)
    if opacity >= 0.999:
        return overlay
    if overlay.mode != "RGBA":
        overlay = overlay.convert("RGBA")
    r, g, b, a = overlay.split()
    a = a.point(lambda px: int(px * opacity))
    return Image.merge("RGBA", (r, g, b, a))


def apply_overlay(base: Image.Image, overlay_spec: OverlaySpec) -> Image.Image:
    base_rgba = base.convert("RGBA")
    overlay = open_image(overlay_spec.path).convert("RGBA")

    mode = overlay_spec.mode
    if mode == "scale_to_canvas":
        overlay = overlay.resize(base_rgba.size, resample=Image.LANCZOS)
        overlay = _apply_opacity(overlay, overlay_spec.opacity)
        return Image.alpha_composite(base_rgba, overlay)

    # For non-full-canvas overlays, paste into a transparent layer first.
    overlay = _apply_opacity(overlay, overlay_spec.opacity)
    layer = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))

    if mode == "center_original":
        x = (base_rgba.width - overlay.width) // 2
        y = (base_rgba.height - overlay.height) // 2
        layer.paste(overlay, (x, y), overlay)
        return Image.alpha_composite(base_rgba, layer)

    if mode == "fit_width":
        new_w = base_rgba.width
        new_h = max(1, int(overlay.height * (new_w / overlay.width)))
        resized = overlay.resize((new_w, new_h), resample=Image.LANCZOS)
        x = 0
        y = (base_rgba.height - resized.height) // 2
        layer.paste(resized, (x, y), resized)
        return Image.alpha_composite(base_rgba, layer)

    if mode == "fit_height":
        new_h = base_rgba.height
        new_w = max(1, int(overlay.width * (new_h / overlay.height)))
        resized = overlay.resize((new_w, new_h), resample=Image.LANCZOS)
        x = (base_rgba.width - resized.width) // 2
        y = 0
        layer.paste(resized, (x, y), resized)
        return Image.alpha_composite(base_rgba, layer)

    raise ValueError(f"Unknown overlay mode: {overlay_spec.mode}")


def apply_studio_overlay(base: Image.Image, studio_spec: dict) -> Image.Image:
    return render_studio_overlay(base, studio_spec)


def _load_font(font_path: Path | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path is not None:
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except OSError:
            pass

    # Common Windows fallback
    try:
        return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _draw_text_with_spacing(draw: ImageDraw.ImageDraw, position: tuple[int, int], text: str,
                            font: ImageFont.ImageFont, fill: tuple[int, int, int, int],
                            stroke_fill: tuple[int, int, int, int], stroke_width: int,
                            letter_spacing: float) -> None:
    x, y = position
    for i, ch in enumerate(text):
        draw.text(
            (x, y),
            ch,
            font=font,
            fill=fill,
            stroke_fill=stroke_fill,
            stroke_width=stroke_width,
        )
        bbox = draw.textbbox((0, 0), ch, font=font, stroke_width=stroke_width)
        ch_w = bbox[2] - bbox[0]
        if i < len(text) - 1:
            x += ch_w + letter_spacing
        else:
            x += ch_w


def draw_number(img: Image.Image, number: int, spec: NumberingSpec) -> Image.Image:
    if not spec.enabled:
        return img

    canvas = img.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    text = str(number)

    font_size = spec.font_size
    if font_size <= 0:
        font_size = max(18, int(canvas.height * 0.09))

    font = _load_font(spec.font_path, font_size)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=spec.stroke_width)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    margin = max(0, spec.margin)
    if spec.position == "custom" and spec.x is not None and spec.y is not None:
        x = max(0, min(canvas.width - text_w, int(spec.x)))
        y = max(0, min(canvas.height - text_h, int(spec.y)))
    elif spec.position == "top-left":
        x, y = margin, margin
    elif spec.position == "top-right":
        x, y = canvas.width - margin - text_w, margin
    elif spec.position == "bottom-left":
        x, y = margin, canvas.height - margin - text_h
    elif spec.position == "center":
        x, y = (canvas.width - text_w) // 2, (canvas.height - text_h) // 2
    else:  # bottom-right
        x, y = canvas.width - margin - text_w, canvas.height - margin - text_h

    fill_color = parse_hex_color(spec.fill) + (255,) if spec.fill_enabled else (0, 0, 0, 0)
    stroke_color = parse_hex_color(spec.stroke_fill) + (255,) if spec.stroke_enabled else (0, 0, 0, 0)
    stroke_width = spec.stroke_width if spec.stroke_enabled else 0
    if spec.letter_spacing > 0:
        _draw_text_with_spacing(draw, (x, y), text, font, fill_color, stroke_color, stroke_width, spec.letter_spacing)
    else:
        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill_color,
            stroke_fill=stroke_color,
            stroke_width=stroke_width,
        )
    return canvas
