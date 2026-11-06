"""Path optimisation and SVG validation for the vectorization engine.

After VTracer produces colour layers this stage removes degenerate paths, drops
the full-canvas background layer when the result should be transparent, and
validates that the assembled SVG is well-formed before it is returned.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET


def _finite_bbox(bbox) -> bool:
    try:
        x, y, w, h = (float(v) for v in bbox)
    except (TypeError, ValueError):
        return False
    return all(math.isfinite(v) for v in (x, y, w, h))


def _covers_canvas(bbox, traced_size) -> bool:
    width, height = traced_size
    if width <= 0 or height <= 0:
        return False
    _, _, w, h = (float(v) for v in bbox)
    return w >= width * 0.98 and h >= height * 0.98


def regions(regions: list[dict], settings: dict, traced_size, has_transparency: bool) -> list[dict]:
    """Clean the parsed layers: drop degenerates and strip a background fill.

    Document order is sacred: VTracer's stacked layers rely on painter's order
    exactly as it emits them; reordering (or flipping fill rules) repaints the
    artwork with giant blobs.
    """
    cleaned = [r for r in regions
               if r.get('d') and r.get('fill') and _finite_bbox(r.get('bbox', []))
               and float(r['bbox'][2]) > 0 and float(r['bbox'][3]) > 0]

    strip_background = has_transparency or bool(settings.get('remove_background', False))
    if strip_background and cleaned and _covers_canvas(cleaned[0]['bbox'], traced_size):
        cleaned = cleaned[1:]

    return cleaned


def _hex_rgb(fill: str) -> tuple[int, int, int] | None:
    if len(fill) != 7 or fill[0] != '#':
        return None
    try:
        return tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]
    except ValueError:
        return None


def dedupe_fills(regions: list[dict], max_distance: float = 14.0) -> list[dict]:
    """Fold near-identical colours into one layer colour.

    Quantisation and edge enhancement can mint dozens of visually identical
    hex fills; each extra colour costs the tracer whole extra layers. The
    largest area per colour wins and everything within ``max_distance`` RGB
    distance adopts it. Geometry and layer order are untouched.
    """
    area: dict[str, float] = {}
    for r in regions:
        area[r['fill']] = area.get(r['fill'], 0.0) + abs(float(r['bbox'][2]) * float(r['bbox'][3]))
    representatives: list[tuple[str, tuple[int, int, int]]] = []
    mapping: dict[str, str] = {}
    for fill in sorted(area, key=area.get, reverse=True):
        rgb = _hex_rgb(fill)
        if rgb is None:
            mapping[fill] = fill
            continue
        for other, orgb in representatives:
            if sum((a - b) ** 2 for a, b in zip(rgb, orgb)) <= max_distance ** 2:
                mapping[fill] = other
                break
        else:
            representatives.append((fill, rgb))
            mapping[fill] = fill
    for r in regions:
        r['fill'] = mapping[r['fill']]
    return regions


def validate_svg(svg: str, max_bytes: int) -> None:
    """Raise ValueError if the SVG is malformed or exceeds the size budget.

    ``svg`` is the wrapper we assemble ourselves, but VTracer supplies the path
    data, so reject any DTD/entity declarations before parsing to keep the
    validator safe against XML entity-expansion attacks.
    """
    if len(svg.encode('utf-8')) > max_bytes:
        raise ValueError('The vector is too complex. Try fewer colors, less detail or more noise filtering.')
    if '<!' in svg:  # no DOCTYPE / ENTITY / processing constructs are expected
        raise ValueError('The generated vector could not be validated. Please try another image.')
    try:
        ET.fromstring(svg)
    except ET.ParseError as exc:
        raise ValueError('The generated vector could not be validated. Please try another image.') from exc
