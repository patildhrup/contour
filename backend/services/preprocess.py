"""Adaptive image preprocessing before VTracer. Smooths pixelation and staircases while keeping sharp edges."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageFilter

from backend.config import MAX_DIMENSION, MAX_PIXELS


@dataclass(frozen=True)
class PrepResult:
    image: Image.Image
    original_size: tuple[int, int]
    scale: int
    notices: list[str]


def _visible_mask(rgba: np.ndarray, remove_background: bool) -> tuple[np.ndarray, list[str]]:
    notices: list[str] = []
    alpha = rgba[:, :, 3]
    if np.any((alpha > 0) & (alpha < 255)):
        notices.append('Partial transparency is converted to a binary mask at 50% opacity.')
    mask = alpha >= 128
    if remove_background:
        near_white = np.all(rgba[:, :, :3] >= 245, axis=2)
        mask = mask & ~near_white
        notices.append('Near-white pixels were removed throughout the image; this is not subject segmentation.')
    return mask, notices


def _edge_preserving_smooth(image: Image.Image, sigma_s: float = 2.0, sigma_r: float = 32.0) -> Image.Image:
    """
    Fast bilateral edge-preserving filter in numpy.
    Smooths pixel noise and staircase steps along contours while keeping sharp color edges.
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
    y, x = np.mgrid[-rad : rad + 1, -rad : rad + 1]
    spatial_w = np.exp(-(x**2 + y**2) / (2 * sigma_s**2)).astype(np.float32)
    padded = np.pad(rgb, ((rad, rad), (rad, rad), (0, 0)), mode='edge')
    out = np.zeros_like(rgb)
    weights = np.zeros((h, w, 1), dtype=np.float32)

    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            sw = spatial_w[dy + rad, dx + rad]
            neighbor = padded[rad + dy : rad + dy + h, rad + dx : rad + dx + w]
            diff = np.sum((neighbor - rgb) ** 2, axis=2, keepdims=True)
            rw = np.exp(-diff / (2 * sigma_r**2)) * sw
            out += neighbor * rw
            weights += rw

    smoothed = np.clip(out / np.maximum(weights, 1e-5), 0, 255).astype(np.uint8)
    smooth_img = Image.fromarray(smoothed)
    smooth_img = smooth_img.filter(ImageFilter.GaussianBlur(0.7))

    if has_alpha:
        return Image.fromarray(np.dstack((np.array(smooth_img), alpha)))
    return smooth_img


def prepare(image: Image.Image, settings: dict) -> PrepResult:
    original_size = image.size
    rgba = np.array(image)
    mask, notices = _visible_mask(rgba, bool(settings.get('remove_background', False)))
    
    smoothing = int(settings.get('smoothing', 1))
    mode = settings.get('mode', 'color')

    # Count unique visible colors to detect flat graphics vs anti-aliased/noisy images
    visible_rgb = rgba[mask, :3] if mask.any() else rgba[:, :, :3].reshape(-1, 3)
    if len(visible_rgb) > 0:
        sample = visible_rgb[:: max(1, len(visible_rgb) // 10000)]
        packed = (sample[:, 0].astype(np.uint32) << 16 | sample[:, 1].astype(np.uint32) << 8 | sample[:, 2].astype(np.uint32))
        unique_count = len(np.unique(packed))
    else:
        unique_count = 0

    # Only smooth when smoothing is requested and image has anti-aliasing / pixelation noise
    if smoothing > 0 and unique_count > 6:
        sigma_s = 1.8 if smoothing == 1 else 2.5
        image = _edge_preserving_smooth(image, sigma_s=sigma_s, sigma_r=32.0)
        rgba = np.array(image)
        mask, _ = _visible_mask(rgba, bool(settings.get('remove_background', False)))

    rgb = rgba[:, :, :3]

    if mode == 'monochrome':
        gray = np.array(Image.fromarray(rgb).convert('L'))
        rgb = np.repeat(np.where(gray < 128, 0, 255)[:, :, None], 3, axis=2).astype('uint8')
        rgb[~mask] = 255
    else:
        rgb[~mask] = 255

    alpha = np.where(mask, 255, 0).astype('uint8')
    prepared = Image.fromarray(np.dstack((rgb, alpha)))
    if not mask.any():
        notices.append('No visible pixels remain after transparency/background filtering.')
        
    return PrepResult(image=prepared, original_size=original_size, scale=1, notices=notices)
