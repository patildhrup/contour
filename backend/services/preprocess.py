"""Preprocessing that feeds the subpixel tracer.

Pixels are labelled against a foreground-only palette, and anti-aliased boundary
pixels keep an estimated coverage fraction so region edges can be located with
subpixel accuracy instead of snapping to pixel centres.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageFilter

from backend.config import MAX_PIXELS, MAX_DIMENSION

OUTSIDE = -1   # pixel is not part of any region (mask boundary or image border)
INTERIOR = -1  # partner value when a pixel has no differently-labelled neighbour
MASK_EDGE = -2  # partner value across the transparency/background mask boundary

# Palette entries closer than this RGB distance are merged, mirroring the
# colour-precision control: fewer bits keep fewer near-duplicate layers.
_MERGE_DISTANCE = {1: 72, 2: 48, 3: 32, 4: 22, 5: 14, 6: 8, 7: 4, 8: 0}


@dataclass(frozen=True)
class PrepResult:
    image: Image.Image
    original_size: tuple[int, int]
    palette: list[tuple[int, int, int]]
    labels: np.ndarray
    coverage: np.ndarray
    partner: np.ndarray
    notices: list[str]


def _visible_mask(rgba: np.ndarray, settings: dict) -> tuple[np.ndarray, list[str]]:
    notices: list[str] = []
    alpha = rgba[:, :, 3]
    threshold = int(settings.get('alpha_threshold', 128))
    if np.any((alpha > 0) & (alpha < 255)):
        notices.append('Partial transparency is treated as a soft edge; the visible boundary follows 50% opacity.')
    mask = alpha >= threshold
    if settings.get('remove_background', False):
        tolerance = int(settings.get('background_tolerance', 10))
        near_background = np.all(rgba[:, :, :3] >= 255 - tolerance, axis=2)
        mask = mask & ~near_background
        notices.append('Near-white pixels were removed throughout the image; this is not subject segmentation.')
    return mask, notices


def _adjust_mask(rgb: np.ndarray, mask: np.ndarray, expand: int) -> tuple[np.ndarray, np.ndarray]:
    if expand < 0:
        mask = np.array(Image.fromarray(mask.astype('uint8') * 255).filter(
            ImageFilter.MinFilter(2 * abs(expand) + 1))) > 0
    elif expand > 0:
        # Grow neighbouring foreground colors with the mask instead of exposing
        # hidden/removed background colors as a fringe.
        rgb = rgb.copy()
        h, w = mask.shape
        for _ in range(expand):
            previous = np.pad(mask, 1)
            pixels = np.pad(rgb, ((1, 1), (1, 1), (0, 0)), mode='edge')
            grown = mask.copy()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                neighbour = previous[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
                added = neighbour & ~grown
                rgb[added] = pixels[1 + dy:1 + dy + h, 1 + dx:1 + dx + w][added]
                grown |= neighbour
            mask = grown
    return rgb, mask


def _quantize(rgb: np.ndarray, mask: np.ndarray, colors: int) -> tuple[np.ndarray, list[tuple[int, int, int]]]:
    """Median-cut palette with robust representatives, plus the label map."""
    visible = rgb[mask]
    empty_palette: list[tuple[int, int, int]] = []
    if not len(visible):
        return np.zeros(rgb.shape[:2], np.int32), empty_palette
    sample = visible[::max(1, len(visible) // 65536)]
    palette_image = Image.fromarray(sample.reshape(1, -1, 3)).quantize(
        colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    # Median-cut stores cluster means, which mix anti-aliased edge pixels into
    # solid fills and wash out the artwork. Use robust cluster representatives.
    labels = np.array(palette_image).ravel()
    palette_values = palette_image.getpalette()
    for label in np.unique(labels):
        representative = np.median(sample[labels == label], axis=0).astype('uint8')
        palette_values[int(label) * 3:int(label) * 3 + 3] = representative.tolist()
    palette_image.putpalette(palette_values)
    indexed = Image.fromarray(rgb).quantize(palette=palette_image, dither=Image.Dither.NONE)
    label_map = np.array(indexed).astype(np.int32)
    used = np.unique(label_map[mask])
    if not len(used):
        return np.zeros(rgb.shape[:2], np.int32), empty_palette
    # Compact label indices to the colours actually present.
    remap = np.zeros(256, np.int32)
    for new, old in enumerate(used):
        remap[int(old)] = new
    label_map = remap[label_map]
    label_map[~mask] = OUTSIDE
    palette = [tuple(int(c) for c in palette_values[int(old) * 3:int(old) * 3 + 3]) for old in used]
    return label_map, palette


def _merge_palette(labels: np.ndarray, palette: list[tuple[int, int, int]], threshold: int):
    """Union near-duplicate colours so noise cannot survive between two layers."""
    if threshold <= 0 or len(palette) < 2:
        return labels, palette
    counts = np.array([(labels == index).sum() for index in range(len(palette))])
    parent = list(range(len(palette)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    colours = np.array(palette, np.float32)
    for i in range(len(palette)):
        for j in range(i + 1, len(palette)):
            if np.linalg.norm(colours[i] - colours[j]) <= threshold:
                a, b = find(i), find(j)
                if a != b:
                    # Keep the dominant colour as the representative.
                    if counts[a] < counts[b]:
                        a, b = b, a
                    parent[b] = a
    groups: dict[int, int] = {}
    for index in range(len(palette)):
        groups.setdefault(find(index), len(groups))
    remap = np.array([groups[find(index)] for index in range(len(palette))], np.int32)
    keep = {}
    for index in range(len(palette)):
        keep[remap[index]] = index
    representative = [palette[keep[target]] for target in sorted(keep)]
    merged = remap[np.clip(labels, 0, len(palette) - 1)]
    merged[labels == OUTSIDE] = OUTSIDE
    return merged, representative


def _estimate_coverage(labels: np.ndarray, rgb: np.ndarray, alpha: np.ndarray,
                       palette: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Coverage fraction of each pixel's own label and its blend partner.

    Boundary pixels are unmixed against the neighbouring colour, so an
    anti-aliased pixel that is 60% region A and 40% region B reports 0.6. Pixels
    across the mask boundary use the alpha channel, or the removed neighbour's
    original colour when both sides are opaque.
    """
    from backend.services.contours import _shift

    h, w = labels.shape
    base = palette[np.clip(labels, 0, len(palette) - 1)]
    inside = labels != OUTSIDE
    coverage = np.ones((h, w), np.float32)
    partner = np.full((h, w), INTERIOR, np.int32)
    best_residual = np.full((h, w), np.inf, np.float32)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        shifted_labels = _shift(labels, dy, dx, OUTSIDE)
        shifted_rgb = _shift(rgb, dy, dx, 0)
        shifted_alpha = _shift(alpha, dy, dx, 0)
        visible_pair = inside & (shifted_labels != OUTSIDE) & (shifted_labels != labels)
        mask_pair = inside & (shifted_labels == OUTSIDE)
        candidates = np.zeros((h, w, 3), np.float32)
        soft = np.zeros((h, w), np.float32)
        if visible_pair.any():
            candidates[visible_pair] = palette[shifted_labels[visible_pair]]
            direction = base - candidates
            denominator = np.sum(direction * direction, axis=2)
            delta = rgb - candidates
            estimated = np.divide(np.sum(delta * direction, axis=2), denominator,
                                  out=np.ones_like(denominator), where=denominator > 1e-6)
            model = candidates + np.clip(estimated, 0.0, 1.0)[:, :, None] * direction
            residual = np.sum((rgb - model) ** 2, axis=2)
            better = visible_pair & (residual < best_residual)
            coverage[better] = np.clip(estimated[better], 0.0, 1.0)
            partner[better] = shifted_labels[better]
            best_residual[better] = residual[better]
        if mask_pair.any():
            partial = mask_pair & ((alpha < 255) | (shifted_alpha < 255))
            candidates[mask_pair] = shifted_rgb[mask_pair]
            direction = base - candidates
            denominator = np.sum(direction * direction, axis=2)
            delta = rgb - candidates
            estimated = np.divide(np.sum(delta * direction, axis=2), denominator,
                                  out=np.ones_like(denominator), where=denominator > 1e-6)
            # Soft alpha: coverage follows the opacity ramp, edge at 50%.
            alpha_coverage = np.clip(alpha.astype(np.float32) / 255.0, 0.0, 1.0)
            estimated = np.where(partial, alpha_coverage, np.clip(estimated, 0.0, 1.0))
            model = candidates + estimated[:, :, None] * direction
            residual = np.sum((rgb - model) ** 2, axis=2)
            better = mask_pair & (residual < best_residual)
            coverage[better] = np.clip(estimated[better], 0.0, 1.0)
            partner[better] = MASK_EDGE
            best_residual[better] = residual[better]
    coverage[~inside] = 0.0
    return coverage, partner


def _edge_preserving_smooth(image: Image.Image, sigma_s: float = 2.0, sigma_r: float = 32.0) -> Image.Image:
    """
    Fast bilateral edge-preserving filter in numpy.
    Smooths pixel noise while keeping sharp colour edges in place.
    """
    arr = np.array(image)
    has_alpha = arr.ndim == 3 and arr.shape[2] == 4
    if has_alpha:
        alpha = arr[:, :, 3]
        rgb = arr[:, :, :3].astype(np.float32)
    else:
        rgb = arr[:, :, :3].astype(np.float32) if arr.ndim == 3 else np.repeat(arr[:, :, None], 3, axis=2).astype(np.float32)
        alpha = None

    h, w, _ = rgb.shape
    rad = 2 if max(h, w) <= 1200 else 1
    y, x = np.mgrid[-rad: rad + 1, -rad: rad + 1]
    spatial_w = np.exp(-(x**2 + y**2) / (2 * sigma_s**2)).astype(np.float32)
    padded = np.pad(rgb, ((rad, rad), (rad, rad), (0, 0)), mode='edge')
    out = np.zeros_like(rgb)
    weights = np.zeros((h, w, 1), dtype=np.float32)

    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            sw = spatial_w[dy + rad, dx + rad]
            neighbour = padded[rad + dy: rad + dy + h, rad + dx: rad + dx + w]
            diff = np.sum((neighbour - rgb) ** 2, axis=2, keepdims=True)
            rw = np.exp(-diff / (2 * sigma_r**2)) * sw
            out += neighbour * rw
            weights += rw

    smoothed = np.clip(out / np.maximum(weights, 1e-5), 0, 255).astype(np.uint8)
    if has_alpha:
        return Image.fromarray(np.dstack((smoothed, alpha)))
    return Image.fromarray(smoothed)


def prepare(image: Image.Image, settings: dict) -> PrepResult:
    original_size = image.size
    if image.width * image.height > MAX_PIXELS or max(image.size) > MAX_DIMENSION:
        raise ValueError('Image exceeds the configured pixel or dimension budget.')
    rgba = np.array(image)
    mask, notices = _visible_mask(rgba, settings)

    smoothing = int(settings.get('smoothing', 1))
    mode = settings.get('mode', 'color')
    mask_expand = int(settings.get('mask_expand', 0))

    # Count unique visible colours to detect flat graphics vs anti-aliased/noisy images.
    visible_rgb = rgba[mask, :3] if mask.any() else rgba[:, :, :3].reshape(-1, 3)
    if len(visible_rgb) > 0:
        sample = visible_rgb[:: max(1, len(visible_rgb) // 10000)]
        packed = (sample[:, 0].astype(np.uint32) << 16 | sample[:, 1].astype(np.uint32) << 8
                  | sample[:, 2].astype(np.uint32))
        unique_count = len(np.unique(packed))
    else:
        unique_count = 0

    # Only denoise when requested and the image carries anti-aliasing or codec noise.
    if smoothing > 0 and unique_count > 6:
        sigma_s = 1.8 if smoothing == 1 else 2.5
        image = _edge_preserving_smooth(image, sigma_s=sigma_s, sigma_r=32.0)
        rgba = np.array(image)
        mask, _ = _visible_mask(rgba, settings)

    rgb = rgba[:, :, :3].astype(np.float32)
    alpha = rgba[:, :, 3]
    if mask_expand:
        rgb_u8, mask = _adjust_mask(np.clip(rgb, 0, 255).astype('uint8'), mask, mask_expand)
        rgb = rgb_u8.astype(np.float32)

    if mode == 'monochrome':
        palette = [(0, 0, 0), (255, 255, 255)]
        lightness = np.array(Image.fromarray(np.clip(rgb, 0, 255).astype('uint8')).convert('L')).astype(np.float32)
        labels = np.where(lightness < 128, 0, 1).astype(np.int32)
    else:
        labels, palette = _quantize(np.clip(rgb, 0, 255).astype('uint8'), mask,
                                    int(settings.get('colors', 16)))
        labels, palette = _merge_palette(labels, palette,
                                         _MERGE_DISTANCE[int(settings.get('color_precision', 6))])
    labels[~mask] = OUTSIDE

    if palette:
        coverage, partner = _estimate_coverage(labels, rgb, alpha, np.array(palette, np.float32))
    else:
        coverage = np.zeros(labels.shape, np.float32)
        partner = np.full(labels.shape, INTERIOR, np.int32)

    # Quantized preview image (debug/tests): flat colours and the binary mask.
    quantized = np.full(rgb.shape, 255, np.uint8)
    visible = labels != OUTSIDE
    quantized[visible] = np.array(palette, np.uint8).reshape(len(palette), 3)[labels[visible]]
    prepared = Image.fromarray(np.dstack((quantized, np.where(mask, 255, 0).astype('uint8'))))
    if not mask.any():
        notices.append('No visible pixels remain after transparency/background filtering.')
    return PrepResult(image=prepared, original_size=original_size, palette=palette,
                      labels=labels, coverage=coverage, partner=partner, notices=notices)
