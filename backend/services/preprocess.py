"""Adaptive image preprocessing before VTracer. Strength follows the image, not a fixed filter stack."""
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


def _packed_unique(rgb: np.ndarray) -> int:
    if rgb.size == 0:
        return 0
    packed = (
        rgb[:, 0].astype(np.uint32) << 16
        | rgb[:, 1].astype(np.uint32) << 8
        | rgb[:, 2].astype(np.uint32)
    )
    return int(np.unique(packed).size)


def _noise_level(rgb: np.ndarray, mask: np.ndarray) -> float:
    if not mask.any():
        return 0.0
    src = rgb.astype(np.int16)
    neighbor = (
        np.roll(src, 1, 0) + np.roll(src, -1, 0) + np.roll(src, 1, 1) + np.roll(src, -1, 1)
    ) // 4
    delta = np.abs(src - neighbor).mean(axis=2)
    return float(delta[mask].mean())


def _choose_scale(width: int, height: int, detail: int, unique_colors: int) -> int:
    longest = max(width, height)
    target = {1: 960, 2: 1400, 3: 1800}[detail]
    if longest >= target:
        return 1
    wanted = min(4, max(2, round(target / max(longest, 1))))
    # Pixel-art palettes stay on integer scales so block edges stay aligned.
    if unique_colors <= 48 and longest <= 512:
        wanted = min(4, max(2, wanted))
    while wanted > 1:
        new_w, new_h = width * wanted, height * wanted
        if new_w * new_h <= MAX_PIXELS and max(new_w, new_h) <= MAX_DIMENSION:
            return wanted
        wanted -= 1
    return 1


def _similar_neighbor_average(rgb: np.ndarray, threshold: int) -> np.ndarray:
    """Edge-aware smooth: average only neighbors whose color is close to the center pixel."""
    height, width, _ = rgb.shape
    padded = np.pad(rgb, ((1, 1), (1, 1), (0, 0)), mode='edge').astype(np.int16)
    center = rgb.astype(np.int16)
    acc = np.zeros((height, width, 3), np.float32)
    weight = np.zeros((height, width, 1), np.float32)
    for dy in range(3):
        for dx in range(3):
            neighbor = padded[dy : dy + height, dx : dx + width]
            dist = np.abs(neighbor - center).sum(axis=2, keepdims=True)
            keep = (dist <= threshold).astype(np.float32)
            acc += neighbor * keep
            weight += keep
    return np.clip(acc / np.maximum(weight, 1), 0, 255).astype(np.uint8)


def _kmeans_quantize(rgb: np.ndarray, mask: np.ndarray, count: int) -> np.ndarray:
    visible = rgb[mask]
    if visible.size == 0:
        return rgb
    unique_count = _packed_unique(visible)
    if unique_count <= count:
        out = rgb.copy()
        out[~mask] = 255
        return out
    sample_n = min(len(visible), 14000)
    sample_idx = np.linspace(0, len(visible) - 1, sample_n).astype(np.int64)
    samples = visible[sample_idx].astype(np.float32)
    order = np.argsort(samples.mean(axis=1))
    centroids = samples[order[np.linspace(0, sample_n - 1, count).astype(np.int64)]]
    for _ in range(8):
        delta = ((samples[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = delta.argmin(axis=1)
        for i in range(count):
            members = samples[labels == i]
            if len(members):
                centroids[i] = members.mean(axis=0)
    assigned = np.empty((len(visible), 3), np.uint8)
    vis = visible.astype(np.float32)
    chunk = 40000
    for start in range(0, len(visible), chunk):
        sl = vis[start : start + chunk]
        delta = ((sl[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        assigned[start : start + chunk] = np.clip(np.round(centroids[delta.argmin(axis=1)]), 0, 255).astype(np.uint8)
    out = np.full(rgb.shape, 255, np.uint8)
    out[mask] = assigned
    return out


def _pillow_quantize(rgb: np.ndarray, mask: np.ndarray, count: int, illustration: bool) -> np.ndarray:
    work = rgb.copy()
    work[~mask] = 255
    image = Image.fromarray(work)
    method = Image.Quantize.MAXCOVERAGE if illustration else Image.Quantize.MEDIANCUT
    quantized = np.array(image.quantize(colors=count, method=method).convert('RGB'))
    quantized[~mask] = 255
    return quantized


def quantize_colors(rgb: np.ndarray, mask: np.ndarray, count: int, illustration: bool) -> np.ndarray:
    visible = int(mask.sum())
    if visible == 0:
        return np.full(rgb.shape, 255, np.uint8)
    if visible <= 180_000 and count <= 32:
        return _kmeans_quantize(rgb, mask, count)
    return _pillow_quantize(rgb, mask, count, illustration)


def prepare(image: Image.Image, settings: dict) -> PrepResult:
    original_size = image.size
    width, height = original_size
    rgba = np.array(image)
    mask, notices = _visible_mask(rgba, bool(settings.get('remove_background', False)))
    rgb = rgba[:, :, :3]
    visible = rgb[mask]
    unique = _packed_unique(visible[:: max(1, len(visible) // 30000)] if len(visible) else visible)
    noise = _noise_level(rgb, mask)
    illustration = unique <= 400 or (unique <= 1200 and max(width, height) <= 1024)
    pixel_art = unique <= 48 and max(width, height) <= 512
    detail = int(settings.get('detail', 2))
    speckle = int(settings.get('speckle', 4))
    scale = _choose_scale(width, height, detail, unique)

    if scale > 1:
        resample = Image.Resampling.NEAREST if pixel_art else Image.Resampling.LANCZOS
        image = image.resize((width * scale, height * scale), resample)
        rgba = np.array(image)
        mask, _ = _visible_mask(rgba, bool(settings.get('remove_background', False)))
        rgb = rgba[:, :, :3]
        notices.append(f'Low-resolution input was scaled {scale}× so curves can be fitted more smoothly.')

    # Noise reduction is skipped on already-flat palettes so small marks survive.
    if speckle > 0 and not pixel_art:
        passes = 1 if noise < 14 and speckle < 12 else 2
        if detail >= 3:
            passes = min(passes, 1)
        threshold = 14 if illustration else 22
        threshold += min(18, speckle // 2)
        for _ in range(passes):
            rgb = _similar_neighbor_average(rgb, threshold)
            rgb[~mask] = 255

    if settings.get('mode') == 'monochrome':
        gray = np.array(Image.fromarray(rgb).convert('L'))
        rgb = np.repeat(np.where(gray < 128, 0, 255)[:, :, None], 3, axis=2).astype('uint8')
        rgb[~mask] = 255
    else:
        colors = max(2, min(64, int(settings.get('colors', 16))))
        rgb = quantize_colors(rgb, mask, colors, illustration)
        if speckle >= 3 and not pixel_art:
            cleaned = Image.fromarray(rgb).filter(ImageFilter.ModeFilter(3))
            rgb = np.array(cleaned)
            rgb[~mask] = 255
        if unique > colors:
            notices.append(f'Palette reduced to {colors} colors to keep region boundaries clean.')

    alpha = np.where(mask, 255, 0).astype('uint8')
    prepared = Image.fromarray(np.dstack((rgb, alpha)))
    if not mask.any():
        notices.append('No visible pixels remain after transparency/background filtering.')
    return PrepResult(image=prepared, original_size=original_size, scale=scale, notices=notices)
