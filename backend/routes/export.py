"""SVG-to-EPS export — pure Python, no external dependencies.

Handles the SVG subset produced by Contour:
  M x y        – absolute moveto
  C x1 y1 x2 y2 x y  – absolute cubic curveto
  L x y        – absolute lineto
  Z / z        – closepath
  fill="#rrggbb"  – fill color
  <g transform="scale(sx sy)"> – coordinate scaling group
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()

_TOKEN = re.compile(
    r'[MmCcLlAaZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'
)


def _parse_path(d: str):
    """Yield (command, [float_args]) from an SVG absolute path d attribute."""
    tokens = _TOKEN.findall(d)
    i = 0
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        args: list[float] = []
        while i < len(tokens) and tokens[i] not in 'MmCcLlAaZz':
            try:
                args.append(float(tokens[i]))
            except ValueError:
                pass
            i += 1
        yield cmd, args


def _hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip('#')
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return r, g, b


def svg_to_eps(svg_text: str) -> bytes:
    """Convert a Contour SVG string to EPS bytes."""
    try:
        # Strip namespace for simpler iteration
        svg_clean = re.sub(r'\sxmlns(?::[^=]+)?="[^"]*"', '', svg_text)
        root = ET.fromstring(svg_clean)
    except ET.ParseError as exc:
        raise ValueError(f'Invalid SVG: {exc}') from exc

    # Parse dimensions from viewBox or width/height
    vb = root.get('viewBox', '')
    if vb:
        parts = re.split(r'[\s,]+', vb.strip())
        vb_x, vb_y, vb_w, vb_h = (float(p) for p in parts[:4])
    else:
        vb_x, vb_y = 0.0, 0.0
        vb_w = float(re.sub(r'[^\d.]', '', root.get('width', '100')) or 100)
        vb_h = float(re.sub(r'[^\d.]', '', root.get('height', '100')) or 100)

    # Collect global scale from the first <g transform="scale(...)"> wrapper
    scale_x, scale_y = 1.0, 1.0
    for elem in root:
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'g':
            transform = elem.get('transform', '')
            m = re.match(
                r'scale\(\s*([\d.eE+\-]+)(?:\s+([\d.eE+\-]+))?\s*\)',
                transform.strip(),
            )
            if m:
                scale_x = float(m.group(1))
                scale_y = float(m.group(2)) if m.group(2) else scale_x
            break

    # Collect all <path> elements (direct children and inside one <g>)
    paths: list[tuple[str, str]] = []
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'path':
            paths.append((elem.get('fill', '#000000'), elem.get('d', '')))

    # EPS coordinate system: Y=0 at bottom, SVG Y=0 at top → flip.
    w_pts = vb_w * scale_x
    h_pts = vb_h * scale_y

    def tx(x: float) -> float:
        return (x - vb_x) * scale_x

    def ty(y: float) -> float:
        return h_pts - (y - vb_y) * scale_y

    def fmt(v: float) -> str:
        s = f'{v:.4f}'.rstrip('0').rstrip('.')
        return s if s not in ('', '-0') else '0'

    buf = io.StringIO()
    buf.write('%!PS-Adobe-3.0 EPSF-3.0\n')
    buf.write(f'%%BoundingBox: 0 0 {int(w_pts)} {int(h_pts)}\n')
    buf.write(f'%%HiResBoundingBox: 0.0 0.0 {w_pts:.4f} {h_pts:.4f}\n')
    buf.write('%%Creator: Contour Vectorizer\n')
    buf.write('%%EndComments\n')
    buf.write('%%BeginProlog\n%%EndProlog\n')
    buf.write('%%Page: 1 1\n')
    buf.write('gsave\n')

    current_color: tuple[float, float, float] | None = None

    for fill_hex, d in paths:
        if not d.strip():
            continue
        try:
            color = _hex_to_rgb(fill_hex)
        except (ValueError, IndexError):
            color = (0.0, 0.0, 0.0)

        if color != current_color:
            buf.write(f'{color[0]:.5f} {color[1]:.5f} {color[2]:.5f} setrgbcolor\n')
            current_color = color

        buf.write('newpath\n')
        has_content = False

        for cmd, args in _parse_path(d):
            if cmd == 'M' and len(args) >= 2:
                buf.write(f'{fmt(tx(args[0]))} {fmt(ty(args[1]))} moveto\n')
                has_content = True
            elif cmd == 'L' and len(args) >= 2:
                buf.write(f'{fmt(tx(args[0]))} {fmt(ty(args[1]))} lineto\n')
            elif cmd == 'C' and len(args) >= 6:
                # SVG: C x1 y1 x2 y2 x y  → PS: x1 y1 x2 y2 x y curveto
                buf.write(
                    f'{fmt(tx(args[0]))} {fmt(ty(args[1]))} '
                    f'{fmt(tx(args[2]))} {fmt(ty(args[3]))} '
                    f'{fmt(tx(args[4]))} {fmt(ty(args[5]))} curveto\n'
                )
            elif cmd in ('Z', 'z'):
                buf.write('closepath\n')
            # A (arc) commands are rare in Contour output; skip gracefully.

        if has_content:
            # Use even-odd fill rule to match SVG fill-rule="evenodd"
            buf.write('eofill\n')

    buf.write('grestore\n')
    buf.write('%%EOF\n')
    return buf.getvalue().encode('latin-1', errors='replace')


class ExportRequest(BaseModel):
    svg: str
    filename: str = 'vector'


@router.post('/export/eps')
def export_eps(req: ExportRequest):
    """Convert Contour SVG to EPS and stream it as a download."""
    if not req.svg or not req.svg.strip():
        raise HTTPException(422, 'No SVG content provided.')
    try:
        eps_bytes = svg_to_eps(req.svg)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        raise HTTPException(500, 'EPS conversion failed. Please try again.')

    stem = re.sub(r'[^a-zA-Z0-9_\-]', '-', req.filename.rsplit('.', 1)[0])[:60] or 'vector'
    return Response(
        content=eps_bytes,
        media_type='application/postscript',
        headers={
            'Content-Disposition': f'attachment; filename="{stem}.eps"',
            'Content-Length': str(len(eps_bytes)),
        },
    )

