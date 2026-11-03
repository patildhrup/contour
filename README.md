# Contour

An image-to-vector studio built with React, TypeScript, FastAPI, Pillow and NumPy, powered by a subpixel contour tracing engine. Upload JPEG, PNG or WebP, tune the trace, compare raster and vector, edit the palette, and download SVG, vector PDF or PNG.

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

Pillow decodes and applies EXIF orientation. A binary alpha/background mask is constructed, optional edge-preserving smoothing runs, and the mask is dilated/eroded. Expansion propagates foreground colors instead of exposing hidden background RGB. Median-cut quantization builds a palette from visible pixels with median cluster representatives so anti-aliased edges do not wash out solid fills; near-duplicate colours are merged according to the colour-precision setting. Anti-aliased boundary pixels are then unmixed into coverage fractions, and each palette colour becomes a coverage field whose 0.5 iso-contour (marching squares with linear interpolation) locates region edges with subpixel accuracy — adjacent regions share boundaries by construction. Contours are denoised with closed-loop simplification and fitted with cubic Bezier curves using shared tangents at smooth joins and independent tangents at detected corners; each colour is one even-odd path containing all its holes, stroked with its own fill colour so hairline seams never appear between coincident boundaries. Angular mode keeps exact polygons. Detail/simplification control the fit tolerance and speckle filtering removes small regions. Very large images are traced within a pixel budget and scaled back to the original dimensions through a group transform.

The preview reconstructs allowed SVG geometry directly as SVG elements, so it stays vector while zooming. SVG and PDF exports are resolution independent; PNG remains a raster format. Curve fitting improves geometry but cannot recover every feature missing from the source, and independent stacked regions do not provide a shared-boundary vector graph.

PDF export preserves path geometry, fill rules and ancestor transforms. Unsupported vector content reports an export error instead of silently rasterizing. PNG is rendered from the current edited SVG in the browser. Original uploads and conversion output are never substituted with sample artwork.

## API

`GET /api/health` reports engine status and configured limits. `POST /api/convert` accepts multipart `file` and the following optional fields:

| Field | Values / default | Purpose |
| --- | --- | --- |
| mode | color / monochrome; color | Color tracing or black/white threshold |
| colors | 2-64; 16 | Maximum quantized palette size |
| color_precision | 1-8; API 8, UI 6 | Near-duplicate palette colour merging (higher keeps more colours) |
| smoothing | 0-2; 1 | Polygons, smooth or extra smooth curves |
| detail | 1-3; 2 | Curve segment detail |
| speckle | 0-64; 4 | Small-region filtering; zero disables |
| corner | 0-2; 1 | Soft, balanced or sharp corners |
| simplify | 0-2; API 0, UI 1 | Curve segment simplification |
| remove_background | boolean; false | Remove near-white pixels throughout the image |
| background_tolerance | 0-120; 10 | Remove pixels with all RGB channels >= 255 minus tolerance |
| alpha_threshold | 1-255; 128 | Binary opacity cutoff |
| mask_expand | -5 to 5; 0 | Foreground mask growth/erosion in pixels |

Success JSON: `{id, svg, width, height, paths, filename, warnings, elapsed_ms}`. API documentation is at http://localhost:8080/docs. Errors cover invalid images/settings (422), unsupported MIME (415), upload limits (413), overload (429), timeout (504) and service errors (500).

## Limits and image behavior

Default limits: 10 MiB upload, 4 million pixels, 4096 pixels per side. Files are checked by declared MIME and decoded format; animated inputs are rejected. EXIF metadata is not copied. Conversion uses disposable temporary storage and a worker subprocess with timeout; an in-process fallback exists for environments without worker support. Results remain in the browser session. The fallback does not provide subprocess isolation or a hard kill timeout.

Background removal is near-white color masking, not subject segmentation, and can remove white artwork details. Alpha is thresholded rather than preserving partial opacity. Gradients become bands; photographs, textures and tiny text can lose detail or produce complex output. Filled paths remain editable, but text is not reconstructed as text and strokes are not reconstructed as centerlines. This is classical tracing, not a claim of parity with proprietary neural vectorization tools.

Configure `MAX_UPLOAD_BYTES`, `MAX_PIXELS`, `MAX_DIMENSION`, `CONVERSION_TIMEOUT`, `MAX_CONCURRENT`, `MAX_SVG_BYTES`, `TRACE_PIXEL_BUDGET` and `CORS_ORIGINS` through the environment (see `backend/config.py`). `VITE_API_BASE_URL` can configure a frontend API origin; local development uses the Vite proxy. Production requires a Python runtime and a built frontend; this repository does not contain a complete production deployment package.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run build
```

Regression tests cover subpixel boundary accuracy against analytically generated coverage fixtures, resample/simplify geometry, corner-aware Bezier fitting, exact rectangles, palette limits, transparent foreground quantization, background/alpha thresholds, mask growth/erosion, empty masks, speckle/angular semantics, hole subpaths and seam attributes, trace pixel budgets, and API validation. Browser checks and remaining limits are recorded in `docs/verification.md`.

The tracing engine is original code; third-party dependency licenses remain with their authors.
