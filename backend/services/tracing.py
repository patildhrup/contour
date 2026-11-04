"""Image decoding and subpixel contour tracing; invoked in a disposable, time-limited process."""
from __future__ import annotations

import io
import math
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.config import MAX_PIXELS, MAX_DIMENSION, MAX_SVG_BYTES, TRACE_PIXEL_BUDGET
from backend.services.contours import trace_regions
from backend.services.preprocess import OUTSIDE, prepare

MIMES = {
    'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp',
    'BMP': 'image/bmp', 'GIF': 'image/gif', 'TIFF': 'image/tiff',
}

# Regions are stroked with their own fill colour so hairline seams between
# coincident boundaries never rasterize as gaps. Rendered width in output pixels.
_SEAM_STROKE = 0.3


class ImageError(ValueError):
    pass


def decode(data: bytes, mime: str) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                fmt = image.format or ''
                if fmt not in MIMES:
                    raise ImageError('Unsupported format. Choose PNG, JPEG, WebP, BMP, GIF or TIFF.')
                if image.width * image.height > MAX_PIXELS or max(image.size) > MAX_DIMENSION:
                    raise ImageError(f'Image exceeds the {MAX_PIXELS:,} pixel or {MAX_DIMENSION}px side limit.')
                if getattr(image, 'n_frames', 1) > 1 and fmt != 'GIF':
                    raise ImageError('Animated images are not supported. Export a single frame first.')
                image.verify()
        with Image.open(io.BytesIO(data)) as image:
            # GIF uses palette mode; convert to RGBA for uniform processing.
            return ImageOps.exif_transpose(image).convert('RGBA')
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageError('This image is damaged or cannot be decoded safely. Please export it again.') from exc


def _int_setting(settings: dict, key: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(settings.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def _bound_resolution(image: Image.Image) -> Image.Image:
    """Trace very large images at reduced resolution to bound tracing time."""
    pixels = image.width * image.height
    if pixels <= TRACE_PIXEL_BUDGET:
        return image
    factor = math.sqrt(TRACE_PIXEL_BUDGET / pixels)
    size = (max(1, round(image.width * factor)), max(1, round(image.height * factor)))
    return image.resize(size, Image.Resampling.LANCZOS)


def _empty_svg(width: int, height: int) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}"/>')


def _build_svg(regions: list[dict], traced_size: tuple[int, int], original_size: tuple[int, int]) -> str:
    """Wrap traced paths in the original coordinate system.

    Region geometry lives in traced-pixel space; a scale group maps it back to
    the uploaded image's dimensions so exports stay pixel-aligned.
    """
    traced_w, traced_h = traced_size
    original_w, original_h = original_size
    scale_x = original_w / traced_w
    scale_y = original_h / traced_h
    # Stroke width is expressed in traced units, so it renders at a constant
    # _SEAM_STROKE in output pixels regardless of the group scale.
    stroke_width = _SEAM_STROKE / min(scale_x, scale_y)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{original_w}" height="{original_h}" '
             f'viewBox="0 0 {original_w} {original_h}">']
    grouped = traced_size != original_size
    if grouped:
        parts.append(f'<g transform="scale({scale_x:.8f} {scale_y:.8f})">')
    for region in regions:
        fill = region['fill']
        parts.append(f'<path fill="{fill}" fill-rule="evenodd" stroke="{fill}" '
                     f'stroke-width="{stroke_width:.4f}" stroke-linejoin="round" d="{region["d"]}"/>')
    if grouped:
        parts.append('</g>')
    parts.append('</svg>')
    return ''.join(parts)


def _apply_crop(image: Image.Image, crop) -> Image.Image:
    """Pre-crop the bitmap before tracing to raise detail and stay in budget."""
    if not crop:
        return image
    try:
        x, y, w, h = (int(round(float(v))) for v in crop)
    except (TypeError, ValueError):
        return image
    x = max(0, min(image.width - 1, x))
    y = max(0, min(image.height - 1, y))
    w = max(1, min(image.width - x, w))
    h = max(1, min(image.height - y, h))
    return image.crop((x, y, x + w, y + h))


def trace(data: bytes, mime: str, settings: dict) -> dict:
    image = decode(data, mime)
    image = _apply_crop(image, settings.get('crop'))
    original_size = image.size
    image = _bound_resolution(image)
    traced_size = image.size

    prepared = prepare(image, settings)
    notices = list(prepared.notices)

    visible = bool((prepared.labels != OUTSIDE).any())
    regions = trace_regions(prepared.labels, prepared.palette, prepared.coverage,
                            prepared.partner, settings) if visible else []
    if not regions:
        svg = _empty_svg(*original_size)
        paths = 0
    else:
        svg = _build_svg(regions, traced_size, original_size)
        paths = len(regions)
    if len(svg.encode()) > MAX_SVG_BYTES:
        raise ImageError('The vector is too complex. Try fewer colors, less detail or more noise filtering.')
    palette = [{'fill': r['fill'], 'count': int(round(r['area'])), 'bbox': r['bbox']}
               for r in regions]
    return {
        'svg': svg,
        'width': original_size[0],
        'height': original_size[1],
        'paths': paths,
        'scale': [original_size[0] / traced_size[0], original_size[1] / traced_size[1]],
        'regions': [{'fill': r['fill'], 'd': r['d'], 'bbox': r['bbox']} for r in regions],
        'palette': palette,
        'warnings': notices,
    }
