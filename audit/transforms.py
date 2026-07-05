"""Transformation battery applied to each image post-baseline-check.

Each function takes a source path and writes a transformed variant next to
it, returning the new path. Order mirrors the project guide: screenshot,
recompress, crop, resize.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

JPEG_RECOMPRESS_QUALITY = 40
CROP_BORDER_FRACTION = 0.08
RESIZE_DOWNSCALE_FACTOR = 0.25


def _variant_path(src: Path, suffix: str) -> Path:
    return src.with_name(f"{src.stem}_{suffix}{src.suffix}")


def screenshot(src: Path) -> Path:
    """Approximate a screenshot: re-encode as a lossy JPEG (strips metadata
    the way a screen-capture pipeline would), since we can't literally
    screenshot a display in a headless CLI.
    """
    out = _variant_path(src, "screenshot")
    with Image.open(src) as img:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        buf.seek(0)
        Image.open(buf).save(out)
    return out


def recompress(src: Path, quality: int = JPEG_RECOMPRESS_QUALITY) -> Path:
    out = _variant_path(src, "recompress")
    with Image.open(src) as img:
        img.convert("RGB").save(out, format="JPEG", quality=quality)
    return out


def crop(src: Path, border_fraction: float = CROP_BORDER_FRACTION) -> Path:
    out = _variant_path(src, "crop")
    with Image.open(src) as img:
        w, h = img.size
        dx, dy = int(w * border_fraction), int(h * border_fraction)
        img.crop((dx, dy, w - dx, h - dy)).save(out)
    return out


def resize(src: Path, downscale_factor: float = RESIZE_DOWNSCALE_FACTOR) -> Path:
    out = _variant_path(src, "resize")
    with Image.open(src) as img:
        w, h = img.size
        small = img.resize((max(1, int(w * downscale_factor)), max(1, int(h * downscale_factor))), Image.LANCZOS)
        small.resize((w, h), Image.LANCZOS).save(out)
    return out


BATTERY = {
    "screenshot": screenshot,
    "recompress": recompress,
    "crop": crop,
    "resize": resize,
}


def apply_battery(src: Path) -> dict[str, Path]:
    """Apply every transformation in the battery, returning name -> output path."""
    return {name: fn(src) for name, fn in BATTERY.items()}
