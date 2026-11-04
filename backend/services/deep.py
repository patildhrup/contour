"""Client for the optional external AI vectorizer (a Hugging Face Gradio Space).

The classic tracer stays the source of truth; this module forwards the bitmap to
the configured Space through Gradio's own REST API and returns the same shape
`trace()` does. When no Space is configured, or the call fails, the route falls
back to the classic engine so a deployment without the AI service keeps working.

Protocol (Gradio >= 5 / ZeroGPU, keeps the Space on the `gradio` SDK):
  POST {base}/gradio_api/call/{ENDPOINT}   body {"data": [<b64 image>, <settings json>]}
       -> {"event_id": "..."}
  GET  {base}/gradio_api/call/{ENDPOINT}/{event_id}   (Server-Sent Events)
       -> event: complete / data: ["<svg ...>..."]
"""
from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request

from backend.config import AI_ENGINE_URL, AI_ENGINE_TOKEN, CONVERSION_TIMEOUT

# Name of the endpoint registered in the Space's app.py (api_name="vectorize").
ENDPOINT = "vectorize"


class DeepEngineError(ValueError):
    pass


def configured() -> bool:
    return bool(AI_ENGINE_URL)


def _auth_headers():
    return {'Authorization': f'Bearer {AI_ENGINE_TOKEN}'} if AI_ENGINE_TOKEN else {}


def _post_json(url: str, obj: dict, extra_headers: dict | None = None) -> dict:
    body = json.dumps(obj).encode('utf-8')
    headers = {'Content-Type': 'application/json', **_auth_headers(), **(extra_headers or {})}
    request = urllib.request.Request(url, data=body, headers=headers, method='POST')
    with urllib.request.urlopen(request, timeout=CONVERSION_TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))


def _read_sse(response) -> list:
    """Consume a Gradio /call SSE stream and return the final output list."""
    event = None
    for raw in response:
        line = raw.decode('utf-8', 'replace').rstrip('\r\n')
        if line.startswith('event:'):
            event = line.split(':', 1)[1].strip()
        elif line.startswith('data:'):
            data = line.split(':', 1)[1].strip()
            if event == 'complete':
                parsed = json.loads(data)
                return parsed if isinstance(parsed, list) else [parsed]
            if event == 'error':
                raise DeepEngineError(f'AI engine error: {data}')
    raise DeepEngineError('AI engine returned no result.')


def _svg_size(svg: str):
    width = re.search(r'\bwidth="([\d.]+)"', svg)
    height = re.search(r'\bheight="([\d.]+)"', svg)
    if width and height:
        return int(float(width.group(1))), int(float(height.group(1)))
    view_box = re.search(r'viewBox="[\d.\- ]+ ([\d.]+) ([\d.]+)"', svg)
    if view_box:
        return int(float(view_box.group(1))), int(float(view_box.group(2)))
    return None, None


def _attr(tag: str, name: str):
    m = re.search(name + r'\s*=\s*"([^"]*)"', tag)
    return m.group(1) if m else None


def _svg_to_regions(svg: str, width, height):
    """Split a flat SVG into the {fill, d, bbox} regions the Studio edits.

    Only hex-filled paths are treated as editable regions; anything else (masks,
    defs) is ignored so the raw SVG stays the render fallback.
    """
    regions = []
    counts = {}
    for tag in re.findall(r'<path\b[^>]*?/?>', svg, re.S):
        d = _attr(tag, 'd')
        fill = _attr(tag, 'fill')
        if not d or not fill or not re.fullmatch(r'#[0-9a-fA-F]{6}', fill):
            continue
        regions.append({'fill': fill.lower(), 'd': d,
                        'bbox': [0, 0, width or 0, height or 0]})
        counts[fill.lower()] = counts.get(fill.lower(), 0) + 1
    palette = [{'fill': f, 'count': c, 'bbox': []} for f, c in counts.items()]
    return regions, palette


def vectorize(data: bytes, mime: str, settings: dict) -> dict:
    if not configured():
        raise DeepEngineError('AI engine not configured on this deployment.')
    base = AI_ENGINE_URL.rstrip('/')
    submit_url = f'{base}/gradio_api/call/{ENDPOINT}'
    payload = {
        'data': [
            base64.b64encode(data).decode('ascii'),
            json.dumps({k: v for k, v in settings.items() if k != 'crop'}),
        ]
    }

    try:
        submission = _post_json(submit_url, payload)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise DeepEngineError(f'AI engine submit failed: {exc}') from exc
    event_id = submission.get('event_id')
    if not event_id:
        raise DeepEngineError('AI engine did not accept the request.')

    try:
        poll_url = f'{base}/gradio_api/call/{ENDPOINT}/{event_id}'
        request = urllib.request.Request(poll_url, headers=_auth_headers(), method='GET')
        with urllib.request.urlopen(request, timeout=CONVERSION_TIMEOUT) as response:
            outputs = _read_sse(response)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DeepEngineError(f'AI engine result failed: {exc}') from exc

    svg = outputs[0] if outputs else None
    if not isinstance(svg, str) or '<svg' not in svg:
        raise DeepEngineError('AI engine returned no vector data.')

    width, height = _svg_size(svg)
    regions, palette = _svg_to_regions(svg, width, height)
    return {
        'svg': svg,
        'width': width,
        'height': height,
        'paths': len(regions) or svg.count('<path'),
        'regions': regions,
        'palette': palette,
        'warnings': [],
    }
