"""Image decoding and subpixel contour tracing; invoked in a disposable, time-limited process."""
from __future__ import annotations

import io
import math
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.config import MAX_PIXELS, MAX_DIMENSION, MAX_SVG_BYTES, TRACE_PIXEL_BUDGET
from backend.services import preprocess, vectorize, optimize

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
                # Only reject implausibly large rasters (bomb-style inputs);
                # ordinary oversize photos are downscaled before tracing.
                if image.width * image.height > MAX_PIXELS * 8 or max(image.size) > MAX_DIMENSION * 4:
                    raise ImageError(f'Image exceeds the {MAX_PIXELS * 8:,} pixel or {MAX_DIMENSION * 4}px side limit.')
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
        # Nonzero winding (the SVG default) is what VTracer's contours assume;
        # even-odd repaints self-intersecting splines as giant filled blobs.
        parts.append(f'<path fill="{fill}" stroke="{fill}" '
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


def _build_palette(regions: list[dict]) -> list[dict]:
    """Summarise one entry per colour: pixel-ish count and unioned bbox."""
    grouped: dict[str, dict] = {}
    for r in regions:
        entry = grouped.setdefault(r['fill'], {'fill': r['fill'], 'count': 0, 'bbox': [0, 0, 0, 0]})
        x, y, w, h = (float(v) for v in r['bbox'])
        entry['count'] += int(round(w * h))
        box = entry['bbox']
        if box[1] == 0 and box[3] == 0:
            box[:] = [x, y, w, h]
        else:
            left, top = min(box[0], x), min(box[1], y)
            right, bottom = max(box[0] + box[2], x + w), max(box[1] + box[3], y + h)
            box[:] = [left, top, right - left, bottom - top]
    return list(grouped.values())


def _fit_within_limits(image: Image.Image) -> tuple[Image.Image, str | None]:
    """Downscale oversize uploads so conversion always produces a result."""
    pixels = image.width * image.height
    if pixels <= MAX_PIXELS and max(image.size) <= MAX_DIMENSION:
        return image, None
    factor = min(math.sqrt(MAX_PIXELS / pixels), MAX_DIMENSION / max(image.size))
    size = (max(1, round(image.width * factor)), max(1, round(image.height * factor)))
    resized = image.resize(size, Image.Resampling.LANCZOS)
    notice = f'Large image was resized from {image.width}×{image.height} to {size[0]}×{size[1]} before tracing.'
    return resized, notice


def trace(data: bytes, mime: str, settings: dict) -> dict:
    image = decode(data, mime)
    image = _apply_crop(image, settings.get('crop'))
    image, resize_notice = _fit_within_limits(image)
    original_size = image.size
    image = _bound_resolution(image)
    traced_size = image.size
    notices: list[str] = []
    if resize_notice:
        notices.append(resize_notice)

    # Resampling bleeds sharp palette boundaries into gradients; for flat-colour
    # artwork snap the resized bitmap back to solid zones so the tracer does not
    # follow thousands of intermediate-colour contours.
    if traced_size != original_size and preprocess.looks_flat_art(image):
        image = preprocess.requantize(image)
        notices.append('Flat-colour artwork was re-quantised after resizing to keep its edges crisp.')

    prepared, prep_notices, has_transparency = preprocess.prepare_image(image, settings)
    notices.extend(prep_notices)
    svg_raw = vectorize.prepared_to_svg(prepared, settings)
    regions = vectorize.svg_to_regions(svg_raw, traced_size)
    regions = optimize.regions(regions, settings, traced_size, has_transparency)
    regions = optimize.dedupe_fills(regions)

    if not regions:
        svg = _empty_svg(*original_size)
        paths = 0
    else:
        svg = _build_svg(regions, traced_size, original_size)
        paths = len(regions)
    try:
        optimize.validate_svg(svg, MAX_SVG_BYTES)
    except ValueError as exc:
        raise ImageError(str(exc))

    return {
        'svg': svg,
        'width': original_size[0],
        'height': original_size[1],
        'paths': paths,
        'scale': [original_size[0] / traced_size[0], original_size[1] / traced_size[1]],
        'regions': [{'fill': r['fill'], 'd': r['d'], 'bbox': r['bbox']} for r in regions],
        'palette': _build_palette(regions),
        'warnings': notices,
    }
