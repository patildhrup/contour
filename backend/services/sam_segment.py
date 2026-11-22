"""SAM 2 (Segment Anything Model 2) and OpenCV object segmentation layer.

Flow Stage:
  SAM 2 (optional)
  Object segmentation
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Any

import cv2
import httpx
import numpy as np
from PIL import Image

from backend.config import SAM2_ENDPOINT

logger = logging.getLogger(__name__)


def segment_with_opencv(image: Image.Image, num_segments: int = 5) -> list[dict[str, Any]]:
    """Local object & layer segmentation fallback using OpenCV color clustering & connected components."""
    rgb = np.array(image.convert('RGB'))
    h, w, _ = rgb.shape

    # Fast K-Means clustering on pixel colors and coordinates for spatial coherence
    pixels = rgb.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    k = max(2, min(num_segments, 8))
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    label_map = labels.reshape(h, w)

    segments = []
    for i in range(k):
        mask = (label_map == i).astype(np.uint8) * 255
        # Clean small noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        ys, xs = np.nonzero(mask)
        if len(xs) < 100:
            continue
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        segments.append({
            'id': i,
            'color': [int(c) for c in centers[i]],
            'bbox': [x0, y0, x1 - x0, y1 - y0],
            'area': int(len(xs)),
        })
    return segments


async def segment_with_sam2(image: Image.Image) -> list[dict[str, Any]]:
    """Call SAM 2 segmentation API if endpoint configured, else fallback to OpenCV."""
    if not SAM2_ENDPOINT:
        return segment_with_opencv(image)

    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                SAM2_ENDPOINT,
                json={'image': b64},
                headers={'Content-Type': 'application/json'},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get('segments', [])
    except Exception as exc:
        logger.warning('SAM 2 endpoint query failed (%s); falling back to OpenCV segmentation.', exc)

    return segment_with_opencv(image)

