"""Bitmap preprocessing that feeds the VTracer vectorization core.

The classic per-colour coverage/label machinery is gone; VTracer quantizes and
traces internally. This stage only cleans the raster the tracer receives:
transparent/background keying, mask growth, edge-preserving denoise and a
monochrome luminance reduction. The result is an RGBA image in the traced-pixel
space the caller started with, plus the notices shown in the Studio.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def _unique_colour_count(rgb: np.ndarray, mask: np.ndarray) -> int:
    """Count distinct visible colours (downsampled) to spot flat graphics."""
    visible = rgb[mask] if mask.any() else rgb.reshape(-1, 3)
    if not len(visible):
        return 0
    sample = visible[:: max(1, len(visible) // 10000)]
    packed = (sample[:, 0].astype(np.uint32) << 16
              | sample[:, 1].astype(np.uint32) << 8
              | sample[:, 2].astype(np.uint32))
    return int(len(np.unique(packed)))


def _visible_alpha(rgba: np.ndarray, settings: dict) -> tuple[np.ndarray, list[str], bool]:
    """Binary foreground mask from alpha, optional near-white background removal.

    Returns the boolean mask, the notices to surface, and whether the source had
    any real transparency (partial or fully transparent pixels).
    """
    notices: list[str] = []
    alpha = rgba[:, :, 3]
    threshold = int(settings.get('alpha_threshold', 128))
    has_transparency = bool(np.any(alpha < threshold))
    if np.any((alpha > 0) & (alpha < 255)):
        notices.append('Partial transparency is treated as a soft edge; the visible boundary follows the opacity cutoff.')
    mask = alpha >= threshold

    if settings.get('remove_background', False):
        tolerance = int(settings.get('background_tolerance', 10))
        near_background = np.all(rgba[:, :, :3] >= 255 - tolerance, axis=2)
        if bool(near_background.any()):
            has_transparency = True
        mask = mask & ~near_background
        notices.append('Near-white pixels were removed throughout the image; this is not subject segmentation.')
    return mask, notices, has_transparency


def _expand_mask(mask: np.ndarray, expand: int) -> np.ndarray:
    """Grow or erode the foreground region with a square morphological kernel."""
    if expand == 0:
        return mask
    ksize = 2 * abs(expand) + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
    binary = (mask.astype(np.uint8)) * 255
    grown = cv2.dilate(binary, kernel) if expand > 0 else cv2.erode(binary, kernel)
    return grown > 0


def _denoise(rgb: np.ndarray, smoothing: int) -> np.ndarray:
    """Edge-preserving bilateral filter; stronger smoothing widens the radius."""
    d = 5 if smoothing <= 1 else 9
    sigma_color = 24.0 if smoothing <= 1 else 40.0
    sigma_space = 12.0 if smoothing <= 1 else 20.0
    # OpenCV wants a 3-channel uint8 BGR/RGB image; keep channel order stable.
    return cv2.bilateralFilter(rgb, d, sigma_color, sigma_space)


def looks_photo_like(rgb: np.ndarray, mask: np.ndarray) -> bool:
    """True only for genuinely photographic content.

    Lots of unique colours alone is not enough: patterned digital art and
    JPEG-compressed illustrations also have thousands of colours but consist
    of flat zones separated by sharp edges. Photos have smooth intensity
    gradients everywhere, which shows up as a non-trivial median adjacent
    pixel difference. Mean-shift on sharp flat art destroys its detail, so
    the gradient test gates the assist.
    """
    if _unique_colour_count(rgb, mask) <= 24:
        return False
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.int16)
    grad = np.abs(np.diff(gray, axis=1))
    return float(np.median(grad)) >= 2.5


def looks_flat_art(image: Image.Image) -> bool:
    """True when a 16-colour palette reproduces the image almost exactly.

    Logos, patterns and illustrations keep a tiny reconstruction error; photos
    and gradients cannot be represented by a small palette.
    """
    rgb = image.convert('RGB')
    quantized = rgb.quantize(colors=16, method=Image.Quantize.MEDIANCUT,
                             dither=Image.Dither.NONE).convert('RGB')
    err = np.abs(np.asarray(rgb).astype(np.int16)
                 - np.asarray(quantized).astype(np.int16)).max(axis=2)
    return float(np.percentile(err, 95)) <= 24


def requantize(image: Image.Image) -> Image.Image:
    """Snap a resampled flat-colour image back to solid palette zones.

    Lanczos rescaling bleeds sharp colour boundaries into gradients, which the
    tracer then follows with thousands of junk layers. Dither-free median-cut
    restores the flat zones; alpha is preserved untouched.
    """
    alpha = np.asarray(image)[:, :, 3]
    out = image.convert('RGB').quantize(
        colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGBA')
    out.putalpha(Image.fromarray(alpha))
    return out


def _edge_assist(rgb: np.ndarray, strength: int) -> np.ndarray:
    """Edge-detection assist for photographs and gradient-heavy artwork.

    Mean-shift filtering collapses noisy gradients into flat colour zones while
    keeping real boundaries; Canny then locates those boundaries. At strength 2
    the edge pixels are darkened so the tracer's colour layers snap to the
    visible contours instead of drifting through the gradient.
    """
    sp, sr = (7, 18.0) if strength >= 2 else (5, 12.0)
    flat = cv2.pyrMeanShiftFiltering(rgb, sp=sp, sr=sr)
    if strength < 2:
        return flat
    gray = cv2.cvtColor(flat, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.33)
    median = float(np.median(blurred))
    lo = int(max(0, min(200, median * 0.66)))
    edges = cv2.Canny(blurred, lo, min(255, lo * 3))
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))
    out = flat.copy()
    out[edges > 0] = (out[edges > 0] * 0.55).astype(np.uint8)
    return out


def prepare_image(image: Image.Image, settings: dict):
    """Return (rgba_image, notices, has_transparency) for the tracer.

    ``image`` is an RGBA PIL image already cropped and resolution-bounded.
    """
    rgba = np.array(image.convert('RGBA'))
    mask, notices, has_transparency = _visible_alpha(rgba, settings)

    smoothing = int(settings.get('smoothing', 1))
    edge_assist = int(settings.get('edge_assist', 1))
    rgb = rgba[:, :, :3].copy()

    # Edge assist replaces plain denoise on photographic images: mean-shift
    # flattening gives the tracer solid colour zones instead of gradient mud.
    # Flat graphics (including patterned art with many colours) keep the
    # lighter bilateral path so their sharp boundaries survive.
    photo_like = edge_assist > 0 and looks_photo_like(rgb, mask) and not looks_flat_art(image)
    if photo_like:
        rgb = _edge_assist(rgb, edge_assist)
    elif smoothing > 0 and _unique_colour_count(rgb, mask) > 6:
        rgb = _denoise(rgb, smoothing)

    expand = int(settings.get('mask_expand', 0))
    mask = _expand_mask(mask, expand)

    mode = settings.get('mode', 'color')
    alpha = np.where(mask, 255, 0).astype(np.uint8)
    if mode == 'monochrome':
        # Reduce to pure black/white. With edge assist on photos an adaptive
        # threshold separates subject from uneven lighting far better than a
        # fixed cutoff; otherwise dark pixels simply form the artwork.
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        if photo_like:
            bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 25, 10)
        else:
            bw = np.where(gray < 128, 0, 255).astype(np.uint8)
        rgb = np.dstack((bw, bw, bw))

    out = np.dstack((rgb, alpha)).astype(np.uint8)
    if not mask.any():
        notices.append('No visible pixels remain after transparency/background filtering.')
    return Image.fromarray(out, 'RGBA'), notices, has_transparency
