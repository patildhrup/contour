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
slots = asyncio.Semaphore(MAX_CONCURRENT)


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
async def convert(
    file: Annotated[UploadFile, File()],
    mode: Annotated[Literal['color', 'monochrome'], Form()] = 'color',
    colors: Annotated[int, Form(ge=2, le=64)] = 16,
    color_precision: Annotated[int, Form(ge=1, le=8)] = 8,
    smoothing: Annotated[int, Form(ge=0, le=2)] = 1,
    detail: Annotated[int, Form(ge=1, le=3)] = 2,
    speckle: Annotated[int, Form(ge=0, le=64)] = 4,
    corner: Annotated[int, Form(ge=0, le=2)] = 1,
    simplify: Annotated[int, Form(ge=0, le=2)] = 0,
    corner_radius: Annotated[int, Form(ge=0, le=8)] = 0,
    remove_background: Annotated[bool, Form()] = False,
    background_tolerance: Annotated[int, Form(ge=0, le=120)] = 10,
    alpha_threshold: Annotated[int, Form(ge=1, le=254)] = 128,
    mask_expand: Annotated[int, Form(ge=-5, le=5)] = 0,
    engine: Annotated[Literal['classic', 'ai'], Form()] = 'classic',
    crop: Annotated[str, Form()] = '',
):
    try:
        _ACCEPTED = {
            'image/png', 'image/jpeg', 'image/webp',
            'image/bmp', 'image/gif', 'image/tiff', 'image/x-tiff',
            'application/octet-stream',
        }
        if file.content_type not in _ACCEPTED:
            raise HTTPException(415, 'Choose a PNG, JPEG, WebP, BMP, GIF or TIFF image.')
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, 'This image exceeds the upload size limit.')
        if not data:
            raise HTTPException(422, 'The uploaded image is empty.')
        try:
            await asyncio.wait_for(slots.acquire(), timeout=0.1)
        except TimeoutError:
            raise HTTPException(429, 'All converters are busy. Please retry in a moment.', headers={'Retry-After': '3'})
        started = time.monotonic()
        root_dir = Path(__file__).resolve().parents[2]
        # Out-of-process tracing needs the repo layout (<root>/backend/worker.py).
        # Serverless deployments (e.g. Vercel) flatten backend/ to the task root,
        # so the subprocess route is skipped there and tracing runs in-process.
        worker_available = (root_dir / 'backend' / 'worker.py').is_file()
        settings = {
            'mode': mode, 'colors': colors, 'color_precision': color_precision,
            'smoothing': smoothing, 'detail': detail, 'speckle': speckle,
            'corner': corner, 'simplify': simplify, 'remove_background': remove_background,
            'corner_radius': corner_radius, 'background_tolerance': background_tolerance,
            'alpha_threshold': alpha_threshold, 'mask_expand': mask_expand,
        }
        crop_box = _parse_crop(crop)
        if crop_box:
            settings['crop'] = crop_box

        # AI engine: forward to the configured external service. When it is
        # unset or the call fails, degrade gracefully to the classic tracer and
        # surface a warning instead of erroring, so the toggle always yields a
        # vector result.
        if engine == 'ai':
            try:
                from backend.services import deep
                from backend.services.tracing import trace, ImageError
                notice = None
                result = None
                if deep.configured():
                    try:
                        result = await asyncio.to_thread(deep.vectorize, data, file.content_type, settings)
                    except Exception as exc:
                        # Any failure talking to the external engine (cold start,
                        # ZeroGPU quota, an unexpected reply shape) must not turn
                        # into a 500; degrade to the classic tracer instead.
                        notice = f'AI engine unavailable ({exc}); used the classic tracer.'
                else:
                    notice = 'AI engine is not configured on this deployment; used the classic tracer.'
                if result is None or 'error' in result:
                    try:
                        result = await asyncio.to_thread(trace, data, file.content_type, settings)
                    except ImageError as inner:
                        raise HTTPException(422, str(inner))
                    if 'error' in result:
                        raise HTTPException(422, result['error'])
                if notice:
                    result['warnings'] = list(result.get('warnings', [])) + [notice]
                return _finish(result, file, started)
            finally:
                slots.release()
        try:
            with tempfile.TemporaryDirectory(prefix='contour-') as directory:
                target = Path(directory)
                (target / 'input').write_bytes(data)
                (target / 'request.json').write_text(json.dumps({'mime': file.content_type, 'settings': settings}))

                env = {**os.environ, 'PYTHONPATH': str(root_dir)}
                result = None

                if sys.platform != 'win32':
                    try:
                        if worker_available:
                            process = await asyncio.create_subprocess_exec(
                                sys.executable, '-m', 'backend.worker', directory,
                                cwd=str(root_dir),
                                env=env,
                                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                            )
                            try:
                                await asyncio.wait_for(process.wait(), timeout=CONVERSION_TIMEOUT)
                            except TimeoutError:
                                raise HTTPException(504, 'Conversion took too long. Reduce image dimensions or detail and retry.')
                            finally:
                                if process.returncode is None:
                                    process.kill()
                                    await process.wait()
                    except (NotImplementedError, OSError):
                        pass
                else:
                    def _run_worker():
                        proc = subprocess.Popen(
                            [sys.executable, '-m', 'backend.worker', directory],
                            cwd=str(root_dir),
                            env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        try:
                            return proc.wait(timeout=CONVERSION_TIMEOUT)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait()
                            raise

                    try:
                        if worker_available:
                            await asyncio.to_thread(_run_worker)
                    except subprocess.TimeoutExpired:
                        raise HTTPException(504, 'Conversion took too long. Reduce image dimensions or detail and retry.')
                    except Exception:
                        pass

                if (target / 'result.json').exists():
                    try:
                        result = json.loads((target / 'result.json').read_text(encoding='utf-8'))
                    except Exception:
                        result = None

                # In serverless environments (e.g. Vercel) where subprocess execution may be restricted
                # or fail to find modules, execute tracing in-process via worker/service logic.
                if result is None:
                    try:
                        from backend.services.tracing import trace, ImageError
                        result = await asyncio.to_thread(trace, data, file.content_type, settings)
                    except ImageError as exc:
                        raise HTTPException(422, str(exc))
                    except HTTPException:
                        raise
                    except Exception as exc:
                        import traceback, logging
                        logging.error('Tracing failed: %s\n%s', exc, traceback.format_exc())
                        raise HTTPException(422, 'The tracing engine could not process this image. Try another image.')

                if 'error' in result:
                    raise HTTPException(422, result['error'])
        finally:
            slots.release()
        return _finish(result, file, started)
    finally:
        await file.close()
