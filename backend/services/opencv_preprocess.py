"""OpenCV preprocessing pipeline for vectorization.

Flow Stage:
  OpenCV preprocessing:
  - Denoising (Bilateral, Non-Local Means, Gaussian)
  - Thresholding (Adaptive Gaussian, Otsu, Color Clustering)
  - Edge Detection & Contours (Canny, Sobel, Primitive Extraction)
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def denoise(rgb: np.ndarray, method: str = 'bilateral', strength: int = 1) -> np.ndarray:
    """Denoise RGB bitmap while preserving edge crispness."""
    if method == 'nlmeans':
        # Fast Non-Local Means filter for color images: removes camera grain and compression artifacts
        h = 6.0 if strength <= 1 else 12.0
        h_color = 6.0 if strength <= 1 else 12.0
        return cv2.fastNlMeansDenoisingColored(rgb, None, h, h_color, 7, 21)
    elif method == 'gaussian':
        k = 3 if strength <= 1 else 5
        return cv2.GaussianBlur(rgb, (k, k), 1.0 if strength <= 1 else 2.0)
    elif method == 'none':
        return rgb
    else:  # 'bilateral' default
        d = 5 if strength <= 1 else 9
        sigma_color = 28.0 if strength <= 1 else 45.0
        sigma_space = 14.0 if strength <= 1 else 24.0
        return cv2.bilateralFilter(rgb, d, sigma_color, sigma_space)


def apply_thresholding(gray: np.ndarray, method: str = 'adaptive') -> np.ndarray:
    """Binarize or partition grayscale intensities for shape and contour isolation."""
    if method == 'otsu':
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
    elif method == 'adaptive':
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 8
        )
    return gray


def detect_edges(gray: np.ndarray, method: str = 'canny', blur_first: bool = True) -> np.ndarray:
    """Extract boundary contours using auto-calibrated edge detection."""
    work = cv2.GaussianBlur(gray, (3, 3), 1.0) if blur_first else gray
    if method == 'sobel':
        grad_x = cv2.Sobel(work, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(work, cv2.CV_32F, 0, 1, ksize=3)
        mag = cv2.magnitude(grad_x, grad_y)
        return np.clip(mag, 0, 255).astype(np.uint8)
    elif method == 'none':
        return np.zeros_like(gray)
    else:  # 'canny' default with auto-calibrated thresholds
        v = float(np.median(work))
        sigma = 0.33
        lower = int(max(0, (1.0 - sigma) * v))
        upper = int(min(255, (1.0 + sigma) * v))
        return cv2.Canny(work, lower, upper)


def detect_primitives(binary_mask: np.ndarray, min_area: float = 64.0) -> list[dict]:
    """Detect geometric shapes: circles, ellipses, rectangles, and polygons.

    Returns a list of structured shape descriptors for SVG generation.
    """
    contours, hierarchy = cv2.findContours(binary_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    primitives = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        perimeter = cv2.arcLength(cnt, True)
        if perimeter <= 0:
            continue

        # Check circle/ellipse circularity: 4 * pi * Area / (Perimeter^2)
        circularity = 4 * np.pi * (area / (perimeter * perimeter))
        if circularity > 0.82 and len(cnt) >= 5:
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            circle_area = np.pi * (radius ** 2)
            if 0.80 <= (area / circle_area) <= 1.20:
                primitives.append({
                    'type': 'circle',
                    'cx': round(float(x), 2),
                    'cy': round(float(y), 2),
                    'r': round(float(radius), 2),
                    'area': area,
                })
                continue
            try:
                ellipse = cv2.fitEllipse(cnt)
                (cx, cy), (d1, d2), angle = ellipse
                primitives.append({
                    'type': 'ellipse',
                    'cx': round(float(cx), 2),
                    'cy': round(float(cy), 2),
                    'rx': round(float(d1 / 2), 2),
                    'ry': round(float(d2 / 2), 2),
                    'angle': round(float(angle), 2),
                    'area': area,
                })
                continue
            except cv2.error:
                pass

        # Polygon approximation for rectangles and polygons
        epsilon = 0.02 * perimeter
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, w, h = cv2.boundingRect(approx)
            rect_area = w * h
            if 0.85 <= (area / rect_area) <= 1.15:
                primitives.append({
                    'type': 'rect',
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'area': area,
                })
                continue

        # Arbitrary polygon
        if 3 <= len(approx) <= 12 and cv2.isContourConvex(approx):
            pts = approx.reshape(-1, 2)
            primitives.append({
                'type': 'polygon',
                'points': pts.tolist(),
                'area': area,
            })

    return primitives


def run_opencv_pipeline(image: Image.Image, settings: dict) -> tuple[Image.Image, dict]:
    """Execute the full OpenCV Preprocessing Stage:

    1. Denoising (Bilateral / NLMeans)
    2. Thresholding / Color partitioning
    3. Edge detection
    4. Geometric primitive candidate analysis

    Returns (processed_image, analysis_metadata).
    """
    rgba = np.array(image.convert('RGBA'))
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]

    smoothing = int(settings.get('smoothing', 1))
    denoise_method = settings.get('denoise_method', 'bilateral')
    edge_method = settings.get('edge_detection', 'canny')

    # Step 1: Denoising
    cleaned_rgb = denoise(rgb, method=denoise_method, strength=smoothing)

    # Step 2: Grayscale & Edge Detection
    gray = cv2.cvtColor(cleaned_rgb, cv2.COLOR_RGB2GRAY)
    edges = detect_edges(gray, method=edge_method)

    # Step 3: Thresholding if monochrome or high-contrast edge requested
    mode = settings.get('mode', 'color')
    if mode == 'monochrome':
        thresh_method = settings.get('threshold_method', 'adaptive')
        gray_thresh = apply_thresholding(gray, method=thresh_method)
        cleaned_rgb = np.dstack((gray_thresh, gray_thresh, gray_thresh))

    # Step 4: Detect geometric primitives
    primitives = detect_primitives(edges if edges.any() else (gray < 128).astype(np.uint8) * 255)

    out_rgba = np.dstack((cleaned_rgb, alpha))
    metadata = {
        'denoise_method': denoise_method,
        'edge_method': edge_method,
        'edges_detected': int((edges > 0).sum()),
        'geometric_primitives_found': len(primitives),
        'primitives': primitives[:30],
    }
    return Image.fromarray(out_rgba, 'RGBA'), metadata

