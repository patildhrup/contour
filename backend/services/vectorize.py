"""VTracer vectorization core.

Turns a preprocessed RGBA bitmap into a flat, stacked SVG and parses that SVG
back into the ``{fill, d, bbox}`` regions the Studio edits. The public contract
(colour layers in traced-pixel space) is unchanged from the classic tracer, so
only the geometry source differs.
"""
from __future__ import annotations

import io
import re

import vtracer
from PIL import Image


def _clamp(value, lo, hi, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def _params(settings: dict) -> dict:
    """Map the existing Studio controls onto VTracer's tracing options."""
    colors = _clamp(settings.get('colors', 16), 2, 64, 16)
    smoothing = _clamp(settings.get('smoothing', 1), 0, 2, 1)
    detail = _clamp(settings.get('detail', 2), 1, 3, 2)
    speckle = _clamp(settings.get('speckle', 4), 0, 64, 4)
    corner = _clamp(settings.get('corner', 1), 0, 2, 1)
    corner_radius = _clamp(settings.get('corner_radius', 0), 0, 8, 0)
    simplify = _clamp(settings.get('simplify', 0), 0, 2, 0)
    color_precision = _clamp(settings.get('color_precision', 6), 1, 8, 6)

    corner_threshold = {0: 60, 1: 100, 2: 130}[corner]
    splice_threshold = max(15, 60 - corner_radius * 4)
    # More requested colours => smaller colour step between layers.
    layer_difference = max(1, min(64, round(256 / colors)))

    return {
        'colormode': 'color',
        'hierarchical': 'stacked',
        'mode': 'polygon' if smoothing == 0 else 'spline',
        'filter_speckle': speckle,
        'color_precision': color_precision,
        'layer_difference': layer_difference,
        'corner_threshold': corner_threshold,
        'length_threshold': 4 + simplify * 2,
        'max_iterations': max(1, 10 + (detail - 2) * 4 - simplify * 2),
        'splice_threshold': splice_threshold,
        'path_precision': {1: 2, 2: 3, 3: 4}[detail],
    }


def prepared_to_svg(image: Image.Image, settings: dict) -> str:
    """Encode the RGBA bitmap and run VTracer, returning the raw SVG string."""
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return vtracer.convert_raw_image_to_svg(buffer.getvalue(), img_format='png', **_params(settings))


_NUMBER = re.compile(r'-?\d*\.?\d+(?:[eE][-+]?\d+)?')
_HEX = re.compile(r'#[0-9a-fA-F]{6}')
_TRANSLATE = re.compile(r'translate\s*\(\s*([^,\s)]+)(?:[\s,]+([^)\s]+))?\s*\)')


def _apply_translate(d: str, tx: float, ty: float) -> str:
    """Bake a ``translate(tx, ty)`` into the path data.

    VTracer emits every layer as a unit-anchored path positioned with an SVG
    ``transform``; the Studio contract needs geometry in canvas space, so the
    offset is folded into the absolute M/C/L coordinates here. Relative or
    arc-heavy data (never produced by the tracer) is left untouched rather
    than risk corrupting it.
    """
    if tx == 0 and ty == 0:
        return d
    # Relative commands and single-axis V/H do not fit the pairwise shift;
    # the tracer never emits them, but leave such data untouched if it does.
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
    return match.group(1) if match else None


def svg_to_regions(svg: str, traced_size) -> list[dict]:
    """Split a flat stacked SVG into editable ``{fill, d, bbox}`` regions.

    Only hex-filled paths become regions; VTracer's stacked layers are already
    boolean-differenced solid blobs, so each path is one self-contained layer and
    they are kept separate (never merged) to preserve their stacking.
    """
    width, height = traced_size
    regions = []
    for tag in re.findall(r'<path\b[^>]*?/?>', svg, re.S):
        d = _attr(tag, 'd')
        fill = _attr(tag, 'fill')
        if not d or not fill or not _HEX.fullmatch(fill):
            continue
        transform = _attr(tag, 'transform')
        if transform:
            match = _TRANSLATE.search(transform)
            if match:
                tx = float(match.group(1))
                ty = float(match.group(2) if match.group(2) is not None else match.group(1))
                d = _apply_translate(d, tx, ty)
        regions.append({'fill': fill.lower(), 'd': d, 'bbox': _bbox_from_path(d, (0, 0, width, height))})
    return regions
