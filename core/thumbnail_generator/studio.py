from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .util import clamp, parse_hex_color


def _apply_opacity(img: Image.Image, opacity: float) -> Image.Image:
    opacity = clamp(opacity, 0.0, 1.0)
    if opacity >= 0.999:
        return img
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda px: int(px * opacity))
    return Image.merge("RGBA", (r, g, b, a))


def _resolve_font_path(font_path: str | None, font_family: str | None) -> Path | None:
    if font_path:
        candidate = Path(font_path)
        if candidate.exists():
            return candidate
    if font_family:
        fonts_dir = Path("C:/Windows/Fonts")
        if fonts_dir.exists():
            lowered = font_family.lower()
            for font_file in fonts_dir.glob("*.[tT][tT][fF]"):
                if lowered in font_file.stem.lower():
                    return font_file
            for font_file in fonts_dir.glob("*.[oO][tT][fF]"):
                if lowered in font_file.stem.lower():
                    return font_file
    return None


def _load_font(font_path: str | None, font_family: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    resolved = _resolve_font_path(font_path, font_family)
    if resolved is not None:
        try:
            return ImageFont.truetype(str(resolved), size=size)
        except OSError:
            pass

    try:
        return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _measure_text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont,
                        stroke_width: int, letter_spacing: float) -> float:
    width = 0.0
    for idx, ch in enumerate(text):
        bbox = draw.textbbox((0, 0), ch, font=font, stroke_width=stroke_width)
        ch_w = bbox[2] - bbox[0]
        width += ch_w
        if idx < len(text) - 1:
            width += letter_spacing
    return width


def _draw_text_with_spacing(draw: ImageDraw.ImageDraw, position: tuple[int, int], text: str,
                            font: ImageFont.ImageFont, fill: tuple[int, int, int, int],
                            stroke_fill: tuple[int, int, int, int], stroke_width: int,
                            letter_spacing: float) -> None:
    x, y = position
    for idx, ch in enumerate(text):
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
        if idx < len(text) - 1:
            x += ch_w + letter_spacing
        else:
            x += ch_w


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int,
               stroke_width: int, letter_spacing: float) -> list[str]:
    if max_width <= 0:
        return [text]

    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        current = words[0]
        for word in words[1:]:
            test = f"{current} {word}"
            if _measure_text_width(draw, test, font, stroke_width, letter_spacing) <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)

    return lines


def _draw_text_layer(element: dict[str, Any], canvas_scale_x: float, canvas_scale_y: float) -> Image.Image:
    text = element.get("text", "")
    width = max(1, int(element.get("width", 100) * canvas_scale_x))
    height = max(1, int(element.get("height", 50) * canvas_scale_y))
    font_size = max(8, int(element.get("fontSize", 32) * (canvas_scale_y + canvas_scale_x) / 2))
    font_family = element.get("fontFamily")
    font_path = element.get("fontPath")
    fill = element.get("fill", "#ffffff")
    stroke_fill = element.get("stroke", "#000000")
    fill_enabled = element.get("fillEnabled", True)
    stroke_enabled = element.get("strokeEnabled", True)
    stroke_width = int(element.get("strokeWidth", 0)) if stroke_enabled else 0
    align = element.get("align", "left")
    line_height = float(element.get("lineHeight", 1.1))
    letter_spacing = float(element.get("letterSpacing", 0)) * (canvas_scale_x + canvas_scale_y) / 2
    opacity = float(element.get("opacity", 1))

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _load_font(font_path, font_family, font_size)

    lines = _wrap_text(draw, text, font, width, stroke_width, letter_spacing)
    y = 0
    for line in lines:
        line_w = _measure_text_width(draw, line, font, stroke_width, letter_spacing)
        if align == "center":
            x = (width - line_w) // 2
        elif align == "right":
            x = max(0, width - line_w)
        else:
            x = 0

        fill_rgba = parse_hex_color(fill) + (255,) if fill_enabled else (0, 0, 0, 0)
        stroke_rgba = parse_hex_color(stroke_fill) + (255,) if stroke_enabled else (0, 0, 0, 0)
        if letter_spacing > 0:
            _draw_text_with_spacing(draw, (int(x), int(y)), line, font, fill_rgba, stroke_rgba, stroke_width, letter_spacing)
        else:
            draw.text(
                (x, y),
                line,
                font=font,
                fill=fill_rgba,
                stroke_fill=stroke_rgba,
                stroke_width=stroke_width,
            )
        y += int(font_size * line_height)

    return _apply_opacity(layer, opacity)


def _draw_image_layer(element: dict[str, Any], canvas_scale_x: float, canvas_scale_y: float) -> Image.Image:
    path_raw = element.get("path")
    if not path_raw:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    path = Path(path_raw)
    if not path.exists():
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    width = max(1, int(element.get("width", 100) * canvas_scale_x))
    height = max(1, int(element.get("height", 100) * canvas_scale_y))
    opacity = float(element.get("opacity", 1))
    preserve = bool(element.get("preserveAspect", True))

    img = Image.open(path).convert("RGBA")
    if preserve:
        resized = ImageOps.contain(img, (width, height), method=Image.LANCZOS)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        offset = ((width - resized.width) // 2, (height - resized.height) // 2)
        layer.paste(resized, offset, resized)
    else:
        layer = img.resize((width, height), resample=Image.LANCZOS)

    return _apply_opacity(layer, opacity)


def render_studio_overlay(base: Image.Image, spec: dict[str, Any]) -> Image.Image:
    if not spec:
        return base

    canvas_w = int(spec.get("width", base.width))
    canvas_h = int(spec.get("height", base.height))
    elements = spec.get("elements", [])

    if not elements:
        return base

    base_rgba = base.convert("RGBA")
    scale_x = base_rgba.width / max(1, canvas_w)
    scale_y = base_rgba.height / max(1, canvas_h)

    composed = base_rgba

    for element in elements:
        element_type = element.get("type")
        x = int(element.get("x", 0) * scale_x)
        y = int(element.get("y", 0) * scale_y)
        rotation = float(element.get("rotation", 0))

        if element_type == "text":
            layer = _draw_text_layer(element, scale_x, scale_y)
        elif element_type == "image":
            layer = _draw_image_layer(element, scale_x, scale_y)
        else:
            continue

        if rotation:
            rotated = layer.rotate(rotation, expand=True, resample=Image.BICUBIC)
            x -= (rotated.width - layer.width) // 2
            y -= (rotated.height - layer.height) // 2
            layer = rotated

        overlay = Image.new("RGBA", composed.size, (0, 0, 0, 0))
        overlay.paste(layer, (x, y), layer)
        composed = Image.alpha_composite(composed, overlay)

    return composed
