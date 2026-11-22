import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from backend.config import MAX_UPLOAD_BYTES, CONVERSION_TIMEOUT, MAX_CONCURRENT

router = APIRouter()


def _parse_crop(raw: str):
    """Parse a 'x,y,w,h' pre-crop string into an int tuple, or None."""
    if not raw or not raw.strip():
        return None
    try:
        parts = [int(round(float(v))) for v in json.loads(raw)] if raw.strip().startswith('[') \
            else [int(round(float(v))) for v in raw.split(',')]
    except (ValueError, TypeError):
        return None
    return parts if len(parts) == 4 else None


def _finish(result: dict, file: UploadFile, started: float) -> dict:
    stem = re.sub(r'[^a-zA-Z0-9_-]+', '-', (file.filename or 'image').replace('\\', '/').split('/')[-1].rsplit('.', 1)[0]).strip('-')[:60] or 'image'
    return {**result, 'id': uuid4().hex, 'filename': f'{stem}-contour.svg', 'elapsed_ms': round((time.monotonic() - started) * 1000)}


@router.post('/convert')
def convert(
    file: Annotated[UploadFile, File()],
    mode: Annotated[Literal['color', 'monochrome'], Form()] = 'color',
    colors: Annotated[int, Form(ge=2, le=64)] = 16,
    color_precision: Annotated[int, Form(ge=1, le=8)] = 8,
    smoothing: Annotated[int, Form(ge=0, le=2)] = 1,
    detail: Annotated[int, Form(ge=1, le=3)] = 2,
    edge_assist: Annotated[int, Form(ge=0, le=2)] = 1,
    speckle: Annotated[int, Form(ge=0, le=64)] = 4,
    corner: Annotated[int, Form(ge=0, le=2)] = 1,
    simplify: Annotated[int, Form(ge=0, le=2)] = 0,
    corner_radius: Annotated[int, Form(ge=0, le=8)] = 0,
    remove_background: Annotated[bool, Form()] = False,
    background_tolerance: Annotated[int, Form(ge=0, le=120)] = 10,
    alpha_threshold: Annotated[int, Form(ge=1, le=254)] = 128,
    mask_expand: Annotated[int, Form(ge=-5, le=5)] = 0,
    crop: Annotated[str, Form()] = '',
    engine: Annotated[str, Form()] = 'hybrid',
    denoise_method: Annotated[str, Form()] = 'bilateral',
    threshold_method: Annotated[str, Form()] = 'none',
    edge_detection: Annotated[str, Form()] = 'canny',
    sam_enabled: Annotated[bool, Form()] = False,
):
    try:
        _ACCEPTED = {
            'image/png', 'image/jpeg', 'image/webp',
            'image/bmp', 'image/gif', 'image/tiff', 'image/x-tiff',
            'application/octet-stream',
        }
        if file.content_type not in _ACCEPTED:
            raise HTTPException(415, 'Choose a PNG, JPEG, WebP, BMP, GIF or TIFF image.')
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, 'This image exceeds the upload size limit.')
        if not data:
            raise HTTPException(422, 'The uploaded image is empty.')
        started = time.monotonic()
        settings = {
            'mode': mode, 'colors': colors, 'color_precision': color_precision,
            'smoothing': smoothing, 'detail': detail, 'speckle': speckle,
            'corner': corner, 'simplify': simplify, 'remove_background': remove_background,
            'corner_radius': corner_radius, 'background_tolerance': background_tolerance,
            'alpha_threshold': alpha_threshold, 'mask_expand': mask_expand,
            'edge_assist': edge_assist,
            'engine': engine,
            'denoise_method': denoise_method,
            'threshold_method': threshold_method,
            'edge_detection': edge_detection,
            'sam_enabled': sam_enabled,
        }
        crop_box = _parse_crop(crop)
        if crop_box:
            settings['crop'] = crop_box

        try:
            from backend.services.tracing import trace, ImageError
            result = trace(data, file.content_type, settings)
            if 'error' in result:
                raise HTTPException(422, result['error'])
        except ImageError as exc:
            raise HTTPException(422, str(exc))
        except HTTPException:
            raise
        except Exception as exc:
            import traceback, logging
            logging.error('Tracing failed: %s\n%s', exc, traceback.format_exc())
            raise HTTPException(422, f'The tracing engine could not process this image: {exc}')
        return _finish(result, file, started)
    finally:
        try:
            file.file.close()
        except Exception:
            pass
