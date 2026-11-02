# Contour

An original image-to-vector studio built with React, TypeScript, Tailwind, FastAPI, Pillow and VTracer. Upload JPG/JPEG, PNG or WebP, tune tracing, inspect synchronized previews, and download genuine SVG paths, PDF documents, or raster PNG. PDF and PNG export convert the finished vector in the browser.

## Run locally

Requires Python 3.12 and Node.js 22. From this project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Copy-Item .env.example .env
# IMPORTANT: always run uvicorn from the project root using the venv Python
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8080
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to port 8080. On macOS/Linux use `.venv/bin/python` instead of the Windows executable. **Always run backend commands from the project root** (`d:\Coding-dev\contour`) so Python resolves the `backend` package correctly. The `.env` file is loaded there.

## Use

1. Browse, drop an image, or choose **Try a sample image**.
2. Adjust palette, color/monochrome mode, smoothing, detail and speckle filtering.
3. Press **Convert to Vector**. The UI shows an indeterminate processing state, then the actual returned SVG.
4. Compare side by side or with the comparison slider; zoom, pan, reset and switch preview backgrounds.
5. Download SVG, PDF or PNG. Settings changes require a fresh conversion.

No account, API key, paid service or external AI model is required. This is classical automatic tracing, not proprietary neural vectorization. The small landing-page demo is original artwork traced by the same pipeline; it is not substituted for uploaded results. Regenerate it with `python -m backend.generate_demo`.

## API

`GET /api/health` reports engine version and configured upload/dimension limits.

`POST /api/convert` accepts multipart `file` plus these fields:

| Field | Values/default | Meaning |
| --- | --- | --- |
| `mode` | `color` / `monochrome`; color | Grayscale threshold for monochrome |
| `colors` | 2–64; 16 | Pillow palette size before tracing |
| `smoothing` | 0–2; 1 | Polygon, spline, or softer corner threshold |
| `detail` | 1–3; 2 | Curve fitting segment length |
| `speckle` | 0–64; 4 | VTracer small-region filtering |
| `remove_background` | boolean; false | Remove pixels with all RGB channels ≥245 |

Success JSON: `{id, svg, width, height, paths, filename, warnings, elapsed_ms}`. The browser creates a Blob for download. There is no stored-results endpoint because inputs/results are not retained. Open `/docs` on port 8080 for generated API documentation.

Errors: 413 upload size, 415 unsupported MIME, 422 corrupt image/signature mismatch/invalid settings or unsupported animation, 429 converter busy, 504 processing timeout, 500 unexpected service error. Responses do not disclose paths or traces.

## Limits and privacy

Defaults are 10 MiB, 4 million pixels, and 4096 pixels per side. Files are checked by declared MIME **and** Pillow format detection/decoding. EXIF orientation is applied, metadata is not copied. Animated inputs are rejected. Each conversion gets a separate disposable Python process, a UUID and a private temporary directory. The process is killed on timeout; the directory is cleaned after success/error/timeout. Request bodies are bounded before multipart parsing. Temporary storage is not archival storage; a host power loss could leave OS temporary files, so production uses an ephemeral tmpfs.

`MAX_UPLOAD_BYTES`, `MAX_PIXELS`, `MAX_DIMENSION`, `CONVERSION_TIMEOUT`, `MAX_CONCURRENT`, `MAX_SVG_BYTES` and comma-separated `CORS_ORIGINS` configure the backend. `VITE_API_BASE_URL` in `frontend/.env` optionally points the frontend to another API origin; use an origin without `/api`. Keep same-origin proxying for simplest deployment.

Existing alpha is thresholded at 50%; partial opacity is not retained. Near-white removal affects white details throughout the image and is not subject segmentation. Gradients become bands, photographs/textures can become complex or lose detail, and tiny lettering may distort. SVGs contain filled shapes rather than editable text or centerline strokes. This does not promise parity with Vectorizer.AI or perfect reconstruction.

## Deployment

### Vercel

Deploy the backend and frontend as separate Vercel projects. The backend must use
the **repository root**, because its modules import the `backend` package.

For `contour-backend`, open **Settings > Build and Deployment**:

- Set **Root Directory** to the repository root (leave the field empty / `.`),
  rather than `backend`.
- Use the **FastAPI** framework preset. Clear custom Build Command, Install
  Command and Output Directory overrides so Vercel uses the preset defaults.
- Deploy with the root `vercel.json`, `main.py`, `requirements.txt` and
  `.python-version`. Python 3.12 installs the pinned backend dependencies.
- Set `CORS_ORIGINS=https://contour-black.vercel.app` in the backend project's
  production environment. Redeploy after changing settings or variables.

The FastAPI preset routes requests to `main.py`, which exports `backend.main.app`.
Do not combine legacy `builds` / `routes` configuration with `rewrites`, or add a
rewrite to `/api/index.py`. The root configuration explicitly includes the backend
files, including the subprocess worker and tracing services.

For `contour-black`, keep **Root Directory** set to `frontend` with the **Vite**
preset, and set `VITE_API_BASE_URL=https://contour-backend.vercel.app`. Redeploy
the frontend if this build-time variable changes.

After deploying, check `https://contour-backend.vercel.app/api/health`: it should
return `status: "ok"` and `engine_ok: true`. Then convert a small PNG in the
frontend to check the native tracing dependency and worker execution too.
If startup still fails, expand a failed invocation in Vercel Runtime Logs and
read the final exception line; the collapsed "could not import" message alone
does not identify a missing module or native-library failure.

Vercel Functions limit request and response bodies to 4.5 MB, including multipart
and JSON overhead, even though this application's container defaults allow larger
files. Keep Vercel uploads and SVG responses below that platform limit; use the
container deployment below when larger payloads are required. See
[Vercel's Python runtime](https://vercel.com/docs/functions/runtimes/python) and
[Function limits](https://vercel.com/docs/functions/limitations).

### Container

```sh
docker compose up --build -d
```

Open http://localhost:8080. Nginx serves the built frontend and proxies the private backend, with request rate/body/time limits. The backend runs as a non-root user with a read-only filesystem, temporary tmpfs, bounded memory/CPU and a health check. Docker configuration is provided but requires Docker and has not been executed in this Windows session. Backend and frontend were tested directly.

The compose port binds to loopback. For a public deployment, place a TLS reverse proxy/load balancer in front, configure your domain, tune limits to measured workload, and supply your operator contact/privacy terms. No billing/authentication service is implemented. One API process is used by default; `MAX_CONCURRENT` applies per process if you add workers. Preserve proxy request limits and do not expose a development Vite server publicly.

This Python/Rust tracing service requires a Python runtime with native dependencies,
such as Vercel's Python Functions or a container/VM; it cannot run inside a
Cloudflare Worker/Sites static deployment.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run build
```

Tests exercise actual PNG/JPEG/WebP conversions and XML paths (no embedded images), palette/monochrome/transparency, invalid files/settings/dimensions/size, animation rejection, CORS, timeout cleanup and overload responses. See `docs/verification.md` for the final browser results.

## Structure and engine choice

- `frontend/`: React/Vite application, reusable UI components and original demo assets.
- `backend/routes/convert.py`: bounded conversion orchestration and response handling.
- `backend/services/tracing.py`: decoding, preprocessing and VTracer integration.
- `backend/worker.py`: isolated worker entrypoint.
- `backend/tests/`: service and API regression tests.
- `deploy/`, `compose.yaml`: production container configuration.
- `docs/reference-research.md`: reference observations, failed REA installation and engine assessment.

VTracer 0.6.15's installed Python API was tested rather than assuming newer CLI options exist. VTracer is MIT-licensed; see its [repository](https://github.com/visioncortex/vtracer). [Potrace](https://potrace.sourceforge.net/) was evaluated for monochrome but not included, avoiding a second native dependency and its GPL/commercial licensing choice. Pillow supplies image decoding and preprocessing. Dependency licenses remain with their authors.
