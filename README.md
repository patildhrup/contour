# Contour

An image-to-vector studio built with React, TypeScript, FastAPI, OpenCV and VTracer, powered by a single unified Contour Vector Engine. Upload JPEG, PNG or WebP, tune the trace, compare raster and vector, edit the palette, and download SVG, vector PDF or PNG.

## Run locally

Requires Python 3.12 and Node.js 22. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8080
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to port 8080. On macOS/Linux use `.venv/bin/python`. Run backend commands from the repository root. No account, API key or external AI model is required.

## Workflow

1. Drop an image, browse files, or try the built-in sample.
2. Choose **Clean curves** for illustrations or **Fine detail** for small features, then adjust palette limit, color/monochrome mode, curve smoothing, corner precision, noise filtering and path simplification as needed.
3. Optionally remove near-white pixels. Adjust white tolerance, opacity cutoff, and mask expansion (positive grows the foreground; negative trims it).
4. Convert to genuine filled SVG paths with subpixel-accurate boundaries using the built-in tracing engine. Later tracing changes automatically retrace after a short debounce. Downloads stay disabled while a result is out of date; canceled/failed retracing can be restarted with Convert to Vector.
5. Compare side by side or with the slider, using synchronized zoom/pan and checkerboard/light/dark backgrounds.
6. Select palette swatches to recolor or match another fill. Matching colors preserves separate paths and their stacking; it does not perform a geometric union. Reset restores the trace palette. Recoloring updates the preview and all exports without tracing again. A new trace resets palette edits.
7. Download SVG, vector PDF or raster PNG at the original dimensions. Fully transparent results export as empty SVG/vector PDF or transparent PNG.

## Pipeline

The Contour Vector Engine runs one pipeline behind `/api/convert`, in four stages:

1. **Preprocessing (OpenCV).** Pillow decodes the upload and applies EXIF orientation. A binary alpha/background mask is built from the opacity cutoff and optional near-white removal; the mask is dilated or eroded for mask growth; an edge-preserving bilateral filter denoises anti-aliased or codec-noisy images while leaving flat graphics untouched; monochrome mode reduces to a pure black/white luminance split. The result is a cleaned RGBA bitmap.
2. **Vectorization (VTracer).** The cleaned bitmap is encoded in-memory and traced by VTracer (`hierarchical=stacked`), which quantizes colours and fits the layers to Bezier curves or polygons. The Studio controls map onto VTracer options: `colors`/`color_precision` to colour separation, `smoothing` to polygon vs spline, `speckle` to `filter_speckle`, `corner`/`corner_radius` to corner and splice thresholds, and `detail`/`simplify` to path precision and curve iteration.
3. **Path optimisation.** The flat SVG is parsed back into editable colour layers (`{fill, d, bbox}` in traced-pixel space); degenerate paths are dropped and, when the source was transparent or background removal is on, the full-canvas base layer is stripped so exports stay transparent.
4. **Validation.** The assembled SVG is checked for well-formedness (rejecting any DTD/entity declarations) and size against `MAX_SVG_BYTES`.

The final SVG is wrapped in the original coordinate system: a `scale` group maps traced-pixel geometry back to the uploaded image so downloads stay pixel-aligned. The preview reconstructs allowed SVG geometry directly as SVG elements, so it stays vector while zooming. SVG and PDF exports are resolution independent; PNG remains a raster format. Tracing improves geometry but cannot recover features missing from the source, and stacked colour layers are independent fills rather than a shared-boundary vector graph.

PDF export preserves path geometry, fill rules and ancestor transforms. Unsupported vector content reports an export error instead of silently rasterizing. PNG is rendered from the current edited SVG in the browser. Original uploads and conversion output are never substituted with sample artwork.

## API

`GET /api/health` reports engine status and configured limits. `POST /api/convert` accepts multipart `file` and the following optional fields:

| Field | Values / default | Purpose |
| --- | --- | --- |
| mode | color / monochrome; color | Colour tracing or black/white luminance split |
| colors | 2-64; 16 | Target colour-layer count (drives VTracer layer separation) |
| color_precision | 1-8; API 8, UI 6 | VTracer colour precision (higher keeps more colours) |
| smoothing | 0-2; 1 | Polygons (0) or spline curves (1/2) |
| detail | 1-3; 2 | Curve detail: path precision and iteration |
| speckle | 0-64; 4 | Minimum region area in pixels (VTracer filter_speckle); zero disables |
| corner | 0-2; 1 | Soft, balanced or sharp corner threshold |
| corner_radius | 0-8; 0 | Corner Control: lower splice threshold to round detected corners |
| simplify | 0-2; API 0, UI 1 | Curve simplification (raises length threshold, cuts iterations) |
| remove_background | boolean; false | Remove near-white pixels throughout the image |
| background_tolerance | 0-120; 10 | Remove pixels with all RGB channels >= 255 minus tolerance |
| alpha_threshold | 1-255; 128 | Binary opacity cutoff |
| mask_expand | -5 to 5; 0 | Foreground mask growth/erosion in pixels |
| crop | `x,y,w,h` px; empty | Pre-crop the bitmap before tracing to raise detail and stay within resolution limits |

Success JSON: `{id, svg, width, height, paths, scale, regions, palette, filename, warnings, elapsed_ms}`. `regions` is the editable layer list (`{fill, d, bbox}` in traced-pixel space) and `palette` reports detected colours with pixel counts; `scale` maps traced coordinates back to the original image, so the browser can rebuild the same SVG after region edits. API documentation is at http://localhost:8080/docs. Errors cover invalid images/settings (422), unsupported MIME (415), upload limits (413), overload (429), timeout (504) and service errors (500).

## Limits and image behavior

Default limits: 10 MiB upload, 4 million pixels, 4096 pixels per side. Files are checked by declared MIME and decoded format; animated inputs are rejected. EXIF metadata is not copied. Conversion uses disposable temporary storage and a worker subprocess with timeout; an in-process fallback exists for environments without worker support. Results remain in the browser session. The fallback does not provide subprocess isolation or a hard kill timeout.

Background removal is near-white colour masking, not subject segmentation, and can remove white artwork details. Alpha is thresholded rather than preserving partial opacity. Gradients become bands; photographs, textures and tiny text can lose detail or produce complex output. Filled paths remain editable, but text is not reconstructed as text and strokes are not reconstructed as centerlines. This is deterministic raster tracing via VTracer, not a claim of parity with proprietary neural vectorization tools.

Configure `MAX_UPLOAD_BYTES`, `MAX_PIXELS`, `MAX_DIMENSION`, `CONVERSION_TIMEOUT`, `MAX_CONCURRENT`, `MAX_SVG_BYTES`, `TRACE_PIXEL_BUDGET` and `CORS_ORIGINS` through the environment (see `backend/config.py`). `VITE_API_BASE_URL` can configure a frontend API origin; local development uses the Vite proxy. Production requires a Python runtime and a built frontend; this repository does not contain a complete production deployment package.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run build
```

Regression tests cover the engine response contract (`svg/width/height/paths/scale/regions/palette/warnings`), colour-layer generation, monochrome reduction to at most two colours, transparent-background stripping, empty masks, supported raster formats, `svg_to_regions` parsing, SVG validation (DTD and size rejection), and API parameter validation. Browser checks and remaining limits are recorded in `docs/verification.md`.

The tracing engine is original orchestration code built on the third-party VTracer vectorizer; third-party dependency licenses remain with their authors.

## Clarity features

Contour runs a single, unified vectorization engine: OpenCV preprocessing feeding the VTracer tracing core. There is no separate AI mode or external model to configure — every upload is processed by this one pipeline behind `/api/convert`.

The engine targets high-clarity output: edge-preserving denoise before tracing, spline or polygon curve fitting, corner and splice control, colour-layer separation, and transparent-background handling that strips the full-canvas base layer. The Studio workspace adds region editing (click to keep/exclude, recolor, merge, remove), palette adjustment, and pre-crop, all reflected in the preview and every export.
