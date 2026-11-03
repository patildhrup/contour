"""Subpixel region tracing from quantized colour labels.

Region boundaries are located from anti-aliased coverage instead of pixel-centre
labels: each label gets a scalar coverage field whose 0.5 iso-contour (marching
squares with linear interpolation) lies on the true edge with subpixel accuracy.
Contours are simplified, then fitted with tangent-continuous cubics while real
corners keep independent tangents. Adjacent regions derive their boundaries from
the same coverage values, so shared edges coincide by construction.
"""
from __future__ import annotations

import numpy as np

from backend.services.curves import fit_closed

# Fitting inputs beyond this many vertices fall back to exact polygons; the
# resampled point count of a full-canvas contour stays well below it.
_MAX_FIT_POINTS = 60000


def _shift(array, dy, dx, fill):
    """out[y, x] = array[y + dy, x + dx], with `fill` outside the array."""
    out = np.full_like(array, fill)
    h, w = array.shape[:2]
    if abs(dy) >= h or abs(dx) >= w:
        return out
    out[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)] = \
        array[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)]
    return out


def _gaussian(field, sigma):
    """Separable Gaussian blur with edge replication."""
    if sigma <= 0:
        return field.astype(np.float32)
    radius = max(1, int(np.ceil(3 * sigma)))
    offsets = np.arange(-radius, radius + 1)
    kernel = np.exp(-offsets * offsets / (2 * sigma * sigma))
    kernel /= kernel.sum()
    h, w = field.shape
    padded = np.pad(field, ((0, 0), (radius, radius)), mode='edge')
    acc = np.zeros_like(field)
    for i, weight in enumerate(kernel):
        acc += weight * padded[:, i:i + w]
    padded = np.pad(acc, ((radius, radius), (0, 0)), mode='edge')
    acc = np.zeros_like(field)
    for i, weight in enumerate(kernel):
        acc += weight * padded[i:i + h, :]
    return acc


def _simplify(points, epsilon):
    """Closed-loop Douglas-Peucker; drops wobble below epsilon."""
    if len(points) < 8 or epsilon <= 0:
        return points
    n = len(points)
    keep = np.zeros(n, bool)
    keep[0] = True
    # b is an exclusive end in [2, n]; the initial pair (0, n) closes the loop.
    stack = [(0, n)]
    while stack:
        a, b = stack.pop()
        span = b - a
        if span < 2:
            continue
        indices = (a + np.arange(1, span)) % n
        chord = points[(a + span) % n] - points[a]
        length = float(np.hypot(chord[0], chord[1]))
        if length < 1e-12:
            distances = np.linalg.norm(points[indices] - points[a], axis=1)
        else:
            delta = points[indices] - points[a]
            distances = np.abs(chord[0] * delta[:, 1] - chord[1] * delta[:, 0]) / length
        far = int(np.argmax(distances))
        if distances[far] > epsilon:
            split = int(indices[far])
            keep[split] = True
            stack.append((a, split))
            stack.append((split, b))
    return points[keep]


def _polygon_area(points):
    x, y = points[:, 0], points[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


_CASES = {
    1: (('B', 'L'),), 2: (('R', 'B'),), 3: (('R', 'L'),), 4: (('T', 'R'),),
    6: (('T', 'B'),), 7: (('T', 'L'),), 8: (('T', 'L'),), 9: (('T', 'B'),),
    11: (('T', 'R'),), 12: (('R', 'L'),), 13: (('R', 'B'),), 14: (('B', 'L'),),
}
_SADDLE = {
    5: {True: (('T', 'R'), ('B', 'L')), False: (('T', 'L'), ('B', 'R'))},
    10: {True: (('T', 'L'), ('B', 'R')), False: (('T', 'R'), ('B', 'L'))},
}


def _iso_loops(field, level=0.5):
    """Closed iso-contours of a field sampled at pixel centres."""
    f = np.pad(np.asarray(field, dtype=np.float32), 1, constant_values=0.0)
    h, w = f.shape
    above = f >= level
    left, right = f[:, :-1], f[:, 1:]
    denom = right - left
    t_h = np.divide(level - left, denom, out=np.zeros_like(left), where=np.abs(denom) > 1e-12)
    top, bottom = f[:-1, :], f[1:, :]
    denom = bottom - top
    t_v = np.divide(level - top, denom, out=np.zeros_like(top), where=np.abs(denom) > 1e-12)

    a, b = above[:-1, :-1], above[:-1, 1:]
    c, d = above[1:, 1:], above[1:, :-1]
    case = (a.astype(np.uint8) << 3) | (b.astype(np.uint8) << 2) | (c.astype(np.uint8) << 1) | d.astype(np.uint8)
    centre = (f[:-1, :-1] + f[:-1, 1:] + f[1:, 1:] + f[1:, :-1]) * 0.25

    hid = np.arange(h)[:, None] * (w - 1) + np.arange(w - 1)[None, :]
    vid = h * (w - 1) + np.arange(h - 1)[:, None] * w + np.arange(w)[None, :]

    def edge(name, yc, xc):
        if name == 'T':
            return hid[yc, xc]
        if name == 'B':
            return hid[yc + 1, xc]
        if name == 'L':
            return vid[yc, xc]
        return vid[yc, xc + 1]

    segments = []
    for value in range(1, 15):
        yc, xc = np.nonzero(case == value)
        if value in _SADDLE:
            inside = centre[yc, xc] >= level
            for mask, table in ((inside, _SADDLE[value][True]), (~inside, _SADDLE[value][False])):
                for first, second in table:
                    segments.append((edge(first, yc[mask], xc[mask]), edge(second, yc[mask], xc[mask])))
        else:
            for first, second in _CASES[value]:
                segments.append((edge(first, yc, xc), edge(second, yc, xc)))

    adjacency = {}
    for first, second in segments:
        for u, v in zip(first.tolist(), second.tolist()):
            adjacency.setdefault(u, []).append(v)
            adjacency.setdefault(v, []).append(u)

    def crossing(edge_id):
        if edge_id < h * (w - 1):
            y, x = divmod(edge_id, w - 1)
            return (x + float(t_h[y, x]), float(y))
        offset = edge_id - h * (w - 1)
        y, x = divmod(offset, w)
        return (float(x), y + float(t_v[y, x]))

    loops = []
    seen = set()
    for start in adjacency:
        if start in seen:
            continue
        loop = []
        current, previous = start, None
        while True:
            seen.add(current)
            loop.append(crossing(current))
            options = adjacency[current]
            if len(options) != 2:
                break
            following = options[0] if options[1] == previous else options[1]
            if following == start:
                break
            previous, current = current, following
            if len(loop) > 2_000_000:
                break
        if len(loop) >= 3:
            points = np.asarray(loop, dtype=np.float64)
            keep = np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 0.02]
            points = points[keep]
            if len(points) >= 3:
                loops.append(points - 1.0)
    return loops


def _format(value):
    text = f'{value:.3f}'.rstrip('0').rstrip('.')
    return text if text not in ('', '-0') else '0'


def _path_data(loops, tolerance, corner_angle, simplify_epsilon, min_area):
    """Fit every loop and join them into one even-odd path."""
    parts = []
    for loop in loops:
        if abs(_polygon_area(loop)) < min_area:
            continue
        simple = _simplify(loop, simplify_epsilon)
        if len(simple) < 3:
            continue
        if tolerance > 0 and len(simple) <= _MAX_FIT_POINTS:
            chunks = fit_closed(simple, tolerance=tolerance, corner_angle=corner_angle)
            if not chunks:
                continue
            head = f'M{_format(chunks[0][0][0])} {_format(chunks[0][0][1])}'
            body = ' '.join('C' + ' '.join(f'{_format(p[0])} {_format(p[1])}' for p in curve[1:])
                            for curve in chunks)
        else:
            # Angular mode or over-budget contours keep exact polygon geometry.
            head = f'M{_format(simple[0][0])} {_format(simple[0][1])}'
            body = ' '.join(f'L{_format(x)} {_format(y)}' for x, y in simple[1:])
        parts.append(f'{head} {body} Z')
    return ' '.join(parts)


def trace_regions(labels, palette, coverage, partner, settings):
    """Build one filled path per palette colour from label/coverage arrays.

    labels: int32 map, -1 outside the visible mask; palette: list of RGB tuples;
    coverage: per-pixel fraction of the pixel's own label; partner: neighbouring
    blend label, -1 when the pixel is interior and -2 across the mask boundary.
    """
    smoothing = int(settings.get('smoothing', 1))
    detail = int(settings.get('detail', 2))
    simplify = int(settings.get('simplify', 0))
    corner = int(settings.get('corner', 1))
    speckle = int(settings.get('speckle', 4))

    sigma = {0: 0.0, 1: 0.65, 2: 1.0}[smoothing]
    tolerance = {1: 1.0, 2: 0.55, 3: 0.3}[detail]
    tolerance *= (1.25 if smoothing == 2 else 1.0) * (1.0 + 0.3 * simplify)
    corner_angle = {0: 105.0, 1: 70.0, 2: 45.0}[corner]
    min_area = max(0, speckle)
    simplify_epsilon = 0.0 if smoothing == 0 else max(0.15, tolerance * 0.55)

    results = []
    height, width = labels.shape
    for index, colour in enumerate(palette):
        support = (labels == index) | (partner == index)
        if not support.any():
            continue
        ys, xs = np.nonzero(support)
        margin = 6
        y0, y1 = max(0, ys.min() - margin), min(height, ys.max() + margin + 1)
        x0, x1 = max(0, xs.min() - margin), min(width, xs.max() + margin + 1)
        window = (slice(y0, y1), slice(x0, x1))
        own = labels[window] == index
        blend = partner[window] == index
        field = np.zeros((y1 - y0, x1 - x0), np.float32)
        field[own] = coverage[window][own]
        field[blend] = 1.0 - coverage[window][blend]
        if field.max() < 0.5:
            continue
        field = _gaussian(field, sigma)
        loops = [loop + (x0, y0) for loop in _iso_loops(field, 0.5)]
        data = _path_data(loops, tolerance if smoothing else 0.0, corner_angle,
                          simplify_epsilon, min_area)
        if not data:
            continue
        area = sum(abs(_polygon_area(loop)) for loop in loops)
        results.append({
            'fill': '#%02x%02x%02x' % tuple(int(round(v)) for v in colour),
            'd': data,
            'area': area,
        })
    # Paint large regions first so small details composite on top.
    results.sort(key=lambda item: -item['area'])
    return results
