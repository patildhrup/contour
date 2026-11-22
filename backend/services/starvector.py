"""StarVector-1B (starvector/starvector-1b-im2svg) Neural Vectorization Engine.

Converts raster images to pure, scalable, editable SVG vector paths using
the StarVector-1B vision-language model, with strict XML validation and
fallback/hybrid synchronization with VTracer.
"""
from __future__ import annotations

import base64
import io
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from PIL import Image

from backend.config import (
    HUGGINGFACE_API_KEY,
    STARVECTOR_ENDPOINT,
    STARVECTOR_MODEL_ID,
)

logger = logging.getLogger(__name__)

# Official System Prompt matching the StarVector-1B contract:
STARVECTOR_SYSTEM_PROMPT = """You are an expert SVG vectorization engine. Your task is to convert the provided raster image into a high-quality, scalable, editable SVG representation.

1. Primary Objective:
Convert the input image into accurate SVG vector paths while preserving the original visual appearance.

2. Image Analysis:
- Analyze image dimensions, shapes, boundaries, contours.
- Identify foreground objects and background regions.
- Detect edges, curves, corners, and enclosed regions.
- Preserve original composition and proportions.

3. Vectorization Requirements:
- Use <path> for complex contours and curves.
- Use <circle> and <ellipse> for circular shapes.
- Use <rect> and <polygon> for geometric shapes.
- Use cubic Bézier curves for smooth boundaries.
- Generate multiple paths when separate objects are present.

4. Strict Restrictions:
- Do not return Base64 images.
- Do not embed the original raster image.
- Do not use <image> elements to simulate vectorization.
- Return valid SVG markup only, starting with <svg and ending with </svg>.
"""

_SVG_REGEX = re.compile(r'<svg\b[^>]*>(?:.*?)</svg>', re.DOTALL | re.IGNORECASE)


def extract_svg(text: str, fallback_size: tuple[int, int]) -> str | None:
    """Extract, clean, and validate SVG markup from model output."""
    if not text:
        return None

    # Strip markdown code blocks
    cleaned = re.sub(r'^```(?:xml|svg)?\s*', '', text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE).strip()

    match = _SVG_REGEX.search(cleaned)
    if not match:
        return None

    svg_content = match.group(0).strip()

    # Reject fake vectorizations (embedded raster or <image> tags)
    if '<image' in svg_content.lower() or 'data:image/' in svg_content.lower():
        logger.warning('StarVector output contained prohibited <image> or base64 tags; rejected.')
        return None

    # Ensure xmlns and viewBox
    width, height = fallback_size
    if 'xmlns=' not in svg_content:
        svg_content = svg_content.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    if 'viewBox=' not in svg_content:
        svg_content = svg_content.replace('<svg', f'<svg viewBox="0 0 {width} {height}"', 1)

    # XML well-formedness validation
    try:
        ET.fromstring(svg_content)
        return svg_content
    except ET.ParseError as err:
        logger.debug('SVG parse error in raw output (%s); attempting auto-repair.', err)
        # Attempt to auto-close unclosed tags
        if not svg_content.endswith('</svg>'):
            svg_content += '</svg>'
        try:
            ET.fromstring(svg_content)
            return svg_content
        except ET.ParseError:
            return None


async def call_starvector_api(image: Image.Image) -> str | None:
    """Generate SVG by querying StarVector-1B via vLLM/SGLang endpoint or Hugging Face Inference API."""
    width, height = image.size
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    b64_img = base64.b64encode(img_bytes).decode('utf-8')

    # Priority 1: Custom local/remote StarVector Endpoint (vLLM / SGLang / OpenAI API compatible)
    if STARVECTOR_ENDPOINT:
        try:
            url = STARVECTOR_ENDPOINT.rstrip('/')
            if not url.endswith('/chat/completions') and not url.endswith('/generate'):
                url += '/v1/chat/completions'

            headers = {'Content-Type': 'application/json'}
            if HUGGINGFACE_API_KEY:
                headers['Authorization'] = f'Bearer {HUGGINGFACE_API_KEY}'

            payload = {
                'model': STARVECTOR_MODEL_ID,
                'messages': [
                    {'role': 'system', 'content': STARVECTOR_SYSTEM_PROMPT},
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': 'Convert this image to scalable editable SVG.'},
                            {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64_img}'}},
                        ],
                    },
                ],
                'temperature': 0.1,
                'max_tokens': 4096,
            }

            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    content = data['choices'][0]['message']['content']
                    svg = extract_svg(content, (width, height))
                    if svg:
                        return svg
        except Exception as exc:
            logger.warning('Querying STARVECTOR_ENDPOINT failed (%s)', exc)

    # Priority 2: Hugging Face Inference API
    if HUGGINGFACE_API_KEY:
        try:
            hf_url = f'https://api-inference.huggingface.co/models/{STARVECTOR_MODEL_ID}'
            headers = {
                'Authorization': f'Bearer {HUGGINGFACE_API_KEY}',
                'Content-Type': 'application/json',
            }
            payload = {
                'inputs': f'data:image/png;base64,{b64_img}',
                'parameters': {
                    'temperature': 0.1,
                    'max_new_tokens': 4096,
                },
            }
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(hf_url, json=payload, headers=headers)
                if res.status_code == 200:
                    res_data = res.json()
                    if isinstance(res_data, list) and len(res_data) > 0:
                        gen_text = res_data[0].get('generated_text', '')
                        svg = extract_svg(gen_text, (width, height))
                        if svg:
                            return svg
        except Exception as exc:
            logger.warning('Querying Hugging Face Inference API failed (%s)', exc)

    return None


def call_starvector_sync(image: Image.Image) -> str | None:
    """Synchronous invocation for the thread-pooled tracing pipeline."""
    width, height = image.size
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    b64_img = base64.b64encode(img_bytes).decode('utf-8')

    # Custom StarVector Endpoint (vLLM / SGLang / OpenAI API compatible)
    if STARVECTOR_ENDPOINT:
        try:
            url = STARVECTOR_ENDPOINT.rstrip('/')
            if not url.endswith('/chat/completions') and not url.endswith('/generate'):
                url += '/v1/chat/completions'

            headers = {'Content-Type': 'application/json'}
            if HUGGINGFACE_API_KEY:
                headers['Authorization'] = f'Bearer {HUGGINGFACE_API_KEY}'

            payload = {
                'model': STARVECTOR_MODEL_ID,
                'messages': [
                    {'role': 'system', 'content': STARVECTOR_SYSTEM_PROMPT},
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': 'Convert this image to scalable editable SVG.'},
                            {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64_img}'}},
                        ],
                    },
                ],
                'temperature': 0.1,
                'max_tokens': 4096,
            }

            with httpx.Client(timeout=6.0) as client:
                res = client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    content = data['choices'][0]['message']['content']
                    svg = extract_svg(content, (width, height))
                    if svg:
                        return svg
        except Exception as exc:
            logger.warning('StarVector sync endpoint query failed (%s)', exc)

    # Hugging Face Inference API
    if HUGGINGFACE_API_KEY:
        try:
            hf_url = f'https://api-inference.huggingface.co/models/{STARVECTOR_MODEL_ID}'
            headers = {
                'Authorization': f'Bearer {HUGGINGFACE_API_KEY}',
                'Content-Type': 'application/json',
            }
            payload = {
                'inputs': f'data:image/png;base64,{b64_img}',
                'parameters': {
                    'temperature': 0.1,
                    'max_new_tokens': 4096,
                },
            }
            with httpx.Client(timeout=6.0) as client:
                res = client.post(hf_url, json=payload, headers=headers)
                if res.status_code == 200:
                    res_data = res.json()
                    if isinstance(res_data, list) and len(res_data) > 0:
                        gen_text = res_data[0].get('generated_text', '')
                        svg = extract_svg(gen_text, (width, height))
                        if svg:
                            return svg
        except Exception as exc:
            logger.warning('StarVector HF sync query failed (%s)', exc)

    return None


def primitives_to_svg_paths(primitives: list[dict[str, Any]], width: int, height: int) -> list[dict]:
    """Convert detected geometric primitives (circles, rects, ellipses) to SVG region elements."""
    regions = []
    for p in primitives:
        ptype = p.get('type')
        if ptype == 'circle':
            cx, cy, r = p['cx'], p['cy'], p['r']
            # Represent circle as exact cubic bezier closed path
            k = 0.552284749831 * r
            d = (
                f'M {cx} {cy - r} '
                f'C {cx + k} {cy - r} {cx + r} {cy - k} {cx + r} {cy} '
                f'C {cx + r} {cy + k} {cx + k} {cy + r} {cx} {cy + r} '
                f'C {cx - k} {cy + r} {cx - r} {cy + k} {cx - r} {cy} '
                f'C {cx - r} {cy - k} {cx - k} {cy - r} {cx} {cy - r} Z'
            )
            regions.append({'fill': '#000000', 'd': d, 'bbox': [cx - r, cy - r, 2 * r, 2 * r]})
        elif ptype == 'rect':
            x, y, w, h = p['x'], p['y'], p['width'], p['height']
            d = f'M {x} {y} L {x + w} {y} L {x + w} {y + h} L {x} {y + h} Z'
            regions.append({'fill': '#000000', 'd': d, 'bbox': [x, y, w, h]})
        elif ptype == 'polygon':
            pts = p.get('points', [])
            if len(pts) >= 3:
                head = f'M {pts[0][0]} {pts[0][1]}'
                body = ' '.join(f'L {pt[0]} {pt[1]}' for pt in pts[1:])
                d = f'{head} {body} Z'
                xs = [pt[0] for pt in pts]
                ys = [pt[1] for pt in pts]
                bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
                regions.append({'fill': '#000000', 'd': d, 'bbox': bbox})

    return regions
