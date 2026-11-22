"""VTracer & StarVector-1B vectorization core.

Turns a preprocessed RGBA bitmap into scalable, editable SVG vectors and parses that SVG
into the ``{fill, d, bbox}`` regions the Studio edits. Supports cubic Béziers, circles,
ellipses, rectangles, and polygons.
"""
from __future__ import annotations

import io
import logging
import re
from typing import Any

import vtracer
from PIL import Image

from backend.config import DEFAULT_ENGINE, STARVECTOR_ENDPOINT
from backend.services.starvector import call_starvector_sync

logger = logging.getLogger(__name__)


def _clamp(value, lo, hi, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def _params(settings: dict) -> dict:
    """Map Studio controls onto VTracer's tracing options."""
    colors = _clamp(settings.get('colors', 16), 2, 64, 16)
    smoothing = _clamp(settings.get('smoothing', 1), 0, 2, 1)
    detail = _clamp(settings.get('detail', 2), 1, 3, 2)
    speckle = _clamp(settings.get('speckle', 4), 0, 64, 4)
    corner = _clamp(settings.get('corner', 1), 0, 2, 1)
    corner_radius = _clamp(settings.get('corner_radius', 0), 0, 8, 0)
    simplify = _clamp(settings.get('simplify', 0), 0, 2, 0)
    color_precision = _clamp(settings.get('color_precision', 6), 1, 8, 6)

    # Corner threshold: angle in degrees to consider a sharp corner vs smooth curve
    # 0 (Soft): 135 deg (keep curves round and flowing)
    # 1 (Balanced): 90 deg
    # 2 (Sharp): 45 deg (crisp sharp geometric corners)
    corner_threshold = {0: 135, 1: 90, 2: 45}[corner]
    splice_threshold = max(20, min(120, 75 - corner_radius * 7))
    # More requested colours => smaller colour step between layers.
    layer_difference = max(1, min(64, round(256 / colors)))

    return {
        'colormode': 'color',
        'hierarchical': 'stacked',
        'mode': 'polygon' if smoothing == 0 else 'spline',
        'filter_speckle': max(0, speckle),
        'color_precision': color_precision,
        'layer_difference': layer_difference,
        'corner_threshold': corner_threshold,
        'length_threshold': max(2, 4 + simplify * 3),
        'max_iterations': max(10, 10 + (detail - 2) * 4),
        'splice_threshold': splice_threshold,
        'path_precision': {1: 2, 2: 3, 3: 4}[detail],
    }


def prepared_to_svg(image: Image.Image, settings: dict) -> tuple[str, str | None]:
    """Convert preprocessed bitmap to SVG.

    Uses StarVector-1B neural model if endpoint configured or explicitly selected, else VTracer.
    Returns (svg_markup, engine_used_notice).
    """
    engine = settings.get('engine', DEFAULT_ENGINE).lower()

    if engine == 'starvector' or (engine == 'hybrid' and STARVECTOR_ENDPOINT):
        try:
            ai_svg = call_starvector_sync(image)
            if ai_svg:
                return ai_svg, 'Traced using StarVector-1B neural vision engine.'
            if engine == 'starvector':
                logger.info('StarVector-1B endpoint not reachable; falling back to OpenCV + VTracer.')
        except Exception as exc:
            logger.warning('StarVector inference attempt failed (%s); using VTracer fallback.', exc)

    # Classical high-precision VTracer engine with OpenCV bilateral preprocessing
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    svg = vtracer.convert_raw_image_to_svg(buffer.getvalue(), img_format='png', **_params(settings))
    return svg, None


_NUMBER = re.compile(r'-?\d*\.?\d+(?:[eE][-+]?\d+)?')
_HEX = re.compile(r'#[0-9a-fA-F]{6}')
_TRANSLATE = re.compile(r'translate\s*\(\s*([^,\s)]+)(?:[\s,]+([^)\s]+))?\s*\)')

NAMED_COLORS = {
    'black': '#000000', 'white': '#ffffff', 'red': '#ff0000', 'green': '#008000',
    'blue': '#0000ff', 'yellow': '#ffff00', 'cyan': '#00ffff', 'magenta': '#ff00ff',
    'gray': '#808080', 'grey': '#808080', 'silver': '#c0c0c0', 'maroon': '#800000',
    'navy': '#000080', 'olive': '#808000', 'purple': '#800080', 'teal': '#008080',
    'orange': '#ffa500', 'pink': '#ffc0cb', 'gold': '#ffd700',
}


def _normalize_fill(fill: str | None) -> str | None:
    """Normalize any SVG color string into standard 6-digit lowercase #rrggbb."""
    if not fill or fill.lower() in ('none', 'transparent'):
        return None
    f = fill.strip()
    if _HEX.fullmatch(f):
        return f.lower()
    if re.fullmatch(r'#[0-9a-fA-F]{3}', f):
        return ('#' + ''.join(c * 2 for c in f[1:])).lower()
    if re.fullmatch(r'#[0-9a-fA-F]{8}', f):
        return f[:7].lower()
    m = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', f, re.IGNORECASE)
    if m:
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        return f'#{r:02x}{g:02x}{b:02x}'
    return NAMED_COLORS.get(f.lower())


def _circle_to_path(cx: float, cy: float, r: float) -> str:
    k = 0.552284749831 * r
    return (
        f'M {cx:g} {cy - r:g} '
        f'C {cx + k:g} {cy - r:g} {cx + r:g} {cy - k:g} {cx + r:g} {cy:g} '
        f'C {cx + r:g} {cy + k:g} {cx + k:g} {cy + r:g} {cx:g} {cy + r:g} '
        f'C {cx - k:g} {cy + r:g} {cx - r:g} {cy + k:g} {cx - r:g} {cy:g} '
        f'C {cx - r:g} {cy - k:g} {cx - k:g} {cy - r:g} {cx:g} {cy - r:g} Z'
    )


def _ellipse_to_path(cx: float, cy: float, rx: float, ry: float) -> str:
    kx = 0.552284749831 * rx
    ky = 0.552284749831 * ry
    return (
        f'M {cx:g} {cy - ry:g} '
        f'C {cx + kx:g} {cy - ry:g} {cx + rx:g} {cy - ky:g} {cx + rx:g} {cy:g} '
        f'C {cx + rx:g} {cy + ky:g} {cx + kx:g} {cy + ry:g} {cx:g} {cy + ry:g} '
        f'C {cx - kx:g} {cy + ry:g} {cx - rx:g} {cy + ky:g} {cx - rx:g} {cy:g} '
        f'C {cx - rx:g} {cy - ky:g} {cx - kx:g} {cy - ry:g} {cx:g} {cy - ry:g} Z'
    )


def _rect_to_path(x: float, y: float, w: float, h: float, rx: float = 0, ry: float = 0) -> str:
    if rx <= 0 and ry <= 0:
        return f'M {x:g} {y:g} L {x + w:g} {y:g} L {x + w:g} {y + h:g} L {x:g} {y + h:g} Z'
    r = min(max(rx, ry), w / 2, h / 2)
    k = 0.552284749831 * r
    return (
        f'M {x + r:g} {y:g} '
        f'L {x + w - r:g} {y:g} '
        f'C {x + w - r + k:g} {y:g} {x + w:g} {y + r - k:g} {x + w:g} {y + r:g} '
        f'L {x + w:g} {y + h - r:g} '
        f'C {x + w:g} {y + h - r + k:g} {x + w - r + k:g} {y + h:g} {x + w - r:g} {y + h:g} '
        f'L {x + r:g} {y + h:g} '
        f'C {x + r - k:g} {y + h:g} {x:g} {y + h - r + k:g} {x:g} {y + h - r:g} '
        f'L {x:g} {y + r:g} '
        f'C {x:g} {y + r - k:g} {x + r - k:g} {y:g} {x + r:g} {y:g} Z'
    )


def _polygon_to_path(points_str: str) -> str:
    nums = [float(n) for n in _NUMBER.findall(points_str)]
    if len(nums) < 4:
        return ''
    pts = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
    return f'M {pts[0][0]:g} {pts[0][1]:g} ' + ' '.join(f'L {p[0]:g} {p[1]:g}' for p in pts[1:]) + ' Z'


def _apply_translate(d: str, tx: float, ty: float) -> str:
    """Bake a ``translate(tx, ty)`` into the path data."""
    if tx == 0 and ty == 0:
        return d
    if any(c in d for c in 'mclhvsaqVH'):
        return d

    def to_abs(match):
        cmd = match.group(1)
        if cmd in 'Zz':
            return cmd
        vals = []
        for i, n in enumerate(_NUMBER.findall(match.group(2))):
            vals.append(float(n) + (tx if i % 2 == 0 else ty))
        return cmd + ' ' + ' '.join(f'{v:g}' for v in vals)

    return re.sub(r'([MLCTVQHSZz])\s*([-\d.eE,+\s]*)', to_abs, d)


def _bbox_from_path(d: str, fallback):
    numbers = [float(n) for n in _NUMBER.findall(d)]
    xs = numbers[0::2]
    ys = numbers[1::2]
    if not xs or not ys:
        return list(fallback)
    return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]


def _attr(tag: str, name: str):
    match = re.search(name + r'\s*=\s*"([^"]*)"', tag)
    if not match:
        match = re.search(name + r"\s*=\s*'([^']*)'", tag)
    return match.group(1) if match else None


def svg_to_regions(svg: str, traced_size: tuple[int, int]) -> list[dict]:
    """Split an SVG into editable ``{fill, d, bbox}`` regions.

    Supports paths as well as geometric shapes (<circle>, <ellipse>, <rect>, <polygon>).
    """
    width, height = traced_size
    regions = []

    # Tag patterns for paths and primitives
    elem_regex = re.compile(r'<(path|circle|ellipse|rect|polygon)\b([^>]*)/?>', re.IGNORECASE)

    for match in elem_regex.finditer(svg):
        elem_type = match.group(1).lower()
        tag_attrs = match.group(0)

        raw_fill = _attr(tag_attrs, 'fill')
        # If no fill or stroke, check style attribute
        if not raw_fill:
            style = _attr(tag_attrs, 'style') or ''
            sm = re.search(r'fill\s*:\s*([^;]+)', style)
            if sm:
                raw_fill = sm.group(1).strip()

        fill = _normalize_fill(raw_fill)
        if not fill:
            continue

        d = ''
        if elem_type == 'path':
            d = _attr(tag_attrs, 'd') or ''
        elif elem_type == 'circle':
            try:
                cx = float(_attr(tag_attrs, 'cx') or 0)
                cy = float(_attr(tag_attrs, 'cy') or 0)
                r = float(_attr(tag_attrs, 'r') or 0)
                if r > 0:
                    d = _circle_to_path(cx, cy, r)
            except (ValueError, TypeError):
                continue
        elif elem_type == 'ellipse':
            try:
                cx = float(_attr(tag_attrs, 'cx') or 0)
                cy = float(_attr(tag_attrs, 'cy') or 0)
                rx = float(_attr(tag_attrs, 'rx') or 0)
                ry = float(_attr(tag_attrs, 'ry') or 0)
                if rx > 0 and ry > 0:
                    d = _ellipse_to_path(cx, cy, rx, ry)
            except (ValueError, TypeError):
                continue
        elif elem_type == 'rect':
            try:
                x = float(_attr(tag_attrs, 'x') or 0)
                y = float(_attr(tag_attrs, 'y') or 0)
                w = float(_attr(tag_attrs, 'width') or 0)
                h = float(_attr(tag_attrs, 'height') or 0)
                rx = float(_attr(tag_attrs, 'rx') or 0)
                ry = float(_attr(tag_attrs, 'ry') or 0)
                if w > 0 and h > 0:
                    d = _rect_to_path(x, y, w, h, rx, ry)
            except (ValueError, TypeError):
                continue
        elif elem_type == 'polygon':
            points = _attr(tag_attrs, 'points')
            if points:
                d = _polygon_to_path(points)

        if not d:
            continue

        transform = _attr(tag_attrs, 'transform')
        if transform:
            t_match = _TRANSLATE.search(transform)
            if t_match:
                tx = float(t_match.group(1))
                ty = float(t_match.group(2) if t_match.group(2) is not None else t_match.group(1))
                d = _apply_translate(d, tx, ty)

        bbox = _bbox_from_path(d, (0, 0, width, height))
        regions.append({'fill': fill, 'd': d, 'bbox': bbox})

    return regions
