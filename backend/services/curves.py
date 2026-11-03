"""Corner-aware, error-bounded cubic fitting of polygon contours.

Shared tangents at recursive splits remove the small direction changes left by
pixel boundaries. Real corners split the fit and retain independent tangents.
Coordinates and tolerances are in the tracing image's pixel space.
"""
from __future__ import annotations

import numpy as np


def _unit(v):
    length = np.linalg.norm(v)
    return v / length if length > 1e-10 else np.array([1., 0.])


def _bezier(curve, t):
    t = np.asarray(t)[:, None]
    return ((1 - t) ** 3 * curve[0] + 3 * (1 - t) ** 2 * t * curve[1]
            + 3 * (1 - t) * t ** 2 * curve[2] + t ** 3 * curve[3])


def _generate(points, t, left, right):
    b0, b1 = (1 - t) ** 3, 3 * t * (1 - t) ** 2
    b2, b3 = 3 * t ** 2 * (1 - t), t ** 3
    a = np.stack((b1[:, None] * left, b2[:, None] * right), axis=2).reshape(-1, 2)
    residual = (points - (b0 + b1)[:, None] * points[0]
                - (b2 + b3)[:, None] * points[-1]).ravel()
    lengths, _, _, _ = np.linalg.lstsq(a, residual, rcond=None)
    distance = np.linalg.norm(points[-1] - points[0])
    # Avoid inverted handles and extreme loops on narrow or nearly straight runs.
    if np.any(lengths < distance * 1e-4) or np.any(lengths > distance * 3):
        lengths = np.array([distance / 3, distance / 3])
    return np.array([points[0], points[0] + left * lengths[0],
                     points[-1] + right * lengths[1], points[-1]])


def _fit(points, left, right, tolerance, depth=0):
    if len(points) == 2:
        length = np.linalg.norm(points[-1] - points[0]) / 3
        return [np.array([points[0], points[0] + left * length,
                          points[-1] + right * length, points[-1]])]
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    t = np.r_[0, np.cumsum(lengths)]
    t /= max(t[-1], 1e-10)
    curve = _generate(points, t, left, right)
    errors = np.sum((_bezier(curve, t) - points) ** 2, axis=1)
    split = max(1, min(len(points) - 2, int(np.argmax(errors))))
    if errors[split] <= tolerance ** 2:
        return [curve]
    # Newton reparameterization allows a long smooth curve to fit points with
    # nonuniform spacing instead of needlessly splitting into more cubics.
    if errors[split] <= (tolerance * 4) ** 2:
        for _ in range(4):
            q = _bezier(curve, t)
            u = t[:, None]
            first = 3 * ((1-u)**2 * (curve[1]-curve[0]) + 2*(1-u)*u * (curve[2]-curve[1]) + u**2*(curve[3]-curve[2]))
            second = 6 * ((1-u)*(curve[2]-2*curve[1]+curve[0]) + u*(curve[3]-2*curve[2]+curve[1]))
            denominator = np.sum(first*first + (q-points)*second, axis=1)
            candidate = t - np.divide(np.sum((q-points)*first, axis=1), denominator,
                                      out=np.zeros_like(t), where=np.abs(denominator)>1e-10)
            if np.any(np.diff(candidate) <= 0) or candidate.min() < 0 or candidate.max() > 1:
                break
            t = candidate
            curve = _generate(points, t, left, right)
            errors = np.sum((_bezier(curve, t) - points) ** 2, axis=1)
            split = max(1, min(len(points)-2, int(np.argmax(errors))))
            if errors[split] <= tolerance ** 2:
                return [curve]
    if depth >= 24:
        # Keep the original boundary for pathological contours, bounding work.
        return [np.array([a, a+(b-a)/3, a+2*(b-a)/3, b]) for a,b in zip(points[:-1],points[1:])]
    tangent = _unit(points[split + 1] - points[split - 1])
    return (_fit(points[:split + 1], left, -tangent, tolerance, depth+1)
            + _fit(points[split:], tangent, right, tolerance, depth+1))


def _resample(vertices, spacing):
    following = np.roll(vertices, -1, axis=0)
    lengths = np.linalg.norm(following - vertices, axis=1)
    counts = np.maximum(1, np.ceil(lengths / spacing).astype(np.int64))
    # Per-edge fractional positions without an explicit Python loop.
    total = int(counts.sum())
    starts = np.repeat(vertices, counts, axis=0)
    ends = np.repeat(following, counts, axis=0)
    offsets = np.concatenate(([0], np.cumsum(counts)))[:-1]
    local = np.arange(total) - np.repeat(offsets, counts)
    fraction = (local / np.repeat(counts, counts)).astype(float)[:, None]
    return starts + fraction * (ends - starts)


def fit_closed(vertices, tolerance=0.6, corner_angle=65., scale=1):
    vertices = np.asarray(vertices, dtype=float)
    if len(vertices) > 1 and np.linalg.norm(vertices[0]-vertices[-1]) < 1e-8:
        vertices = vertices[:-1]
    vertices = vertices[np.r_[True, np.linalg.norm(np.diff(vertices,axis=0),axis=1)>1e-8]]
    if len(vertices) < 3:
        return []
    if len(vertices) == 4:
        edges = np.roll(vertices,-1,axis=0)-vertices
        lengths = np.linalg.norm(edges,axis=1)
        right_angles = np.abs(np.sum(edges*np.roll(edges,-1,axis=0),axis=1))
        if np.all(right_angles < 1e-8 * lengths*np.roll(lengths,-1)):
            # Keep exact rectangles, especially the image's full-canvas fill.
            # Fairing that fill would accidentally clip the exported corners.
            return [np.array([a,a+(b-a)/3,a+2*(b-a)/3,b])
                    for a,b in zip(vertices,np.roll(vertices,-1,axis=0))]
    points = _resample(vertices, max(0.75, scale * 0.75))
    n = len(points)
    if n < 6 or n > 30000:
        return []
    # Look across several pixels, so individual staircase turns do not become
    # false corners. Nonmaximum suppression retains a single anchor per corner.
    support = 3 if corner_angle < 60 else 6
    window = min(max(2, round(support * scale / max(0.75, scale*0.75))), (n-1)//3)
    before = points - np.roll(points, window, axis=0)
    after = np.roll(points, -window, axis=0) - points
    cosine = np.sum(before*after,axis=1) / np.maximum(1e-10,np.linalg.norm(before,axis=1)*np.linalg.norm(after,axis=1))
    angles = np.degrees(np.arccos(np.clip(cosine,-1,1)))
    candidates = np.flatnonzero(angles > corner_angle)
    corners = []
    for index in sorted(candidates, key=lambda i: -angles[i]):
        if all(min(abs(index-c),n-abs(index-c)) > window for c in corners):
            corners.append(int(index))
    # Fair the resampled staircase before fitting. Keep detected corners and
    # their immediate neighborhoods fixed, and cap movement in pixel space.
    original = points.copy()
    for _ in range(2):
        points = (np.roll(points,1,axis=0)+2*points+np.roll(points,-1,axis=0))/4
    displacement = points-original
    magnitude = np.linalg.norm(displacement,axis=1)
    points = original + displacement * np.minimum(1, tolerance*0.75/np.maximum(magnitude,1e-10))[:,None]
    for corner in corners:
        indices=np.arange(corner-window,corner+window+1)%n
        points[indices]=original[indices]
    if not corners:
        anchors = [0, n//2]
    elif len(corners) == 1:
        anchors = sorted([corners[0], (corners[0]+n//2)%n])
    else:
        anchors = sorted(corners)
    curves = []
    corner_set = set(corners)
    for start, end in zip(anchors, anchors[1:]+anchors[:1]):
        indices = np.arange(start, end+1 if end>start else end+n+1)%n
        run = points[indices]
        left = _unit(run[min(window,len(run)-1)]-run[0]) if start in corner_set else _unit(points[(start+window)%n]-points[(start-window)%n])
        right = _unit(run[max(0,len(run)-1-window)]-run[-1]) if end in corner_set else _unit(points[(end-window)%n]-points[(end+window)%n])
        curves.extend(_fit(run,left,right,tolerance))
    return curves
