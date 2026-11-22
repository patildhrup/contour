import backend  # noqa: F401 - Initializes sys.path for local venv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.config import CORS_ORIGINS, MAX_UPLOAD_BYTES, MAX_PIXELS, MAX_DIMENSION
from backend.routes.convert import router
from backend.routes.export import router as export_router


app = FastAPI(title='Contour API', version='1.0.0')
app.include_router(router, prefix='/api')
app.include_router(export_router, prefix='/api')
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['*'],
)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={'detail': 'Invalid upload or conversion settings. Check the options and try again.'})


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    import logging, traceback
    logging.getLogger('contour').error(
        'Unhandled error on %s %s:\n%s', request.method, request.url.path, traceback.format_exc())
    return JSONResponse(status_code=500, content={'detail': 'Conversion is temporarily unavailable. Please try again.'})


@app.get('/')
def root():
    return {
        'name': 'Contour API',
        'status': 'online',
        'version': '1.0.0',
        'health': '/api/health',
        'docs': '/docs',
    }


@app.get('/health')
@app.get('/api/health')
def health():
    return {
        'status': 'ok',
        'engine': 'contour-vector 1.0 (vtracer)',
        'engine_ok': True,
        'max_upload_bytes': MAX_UPLOAD_BYTES,
        'max_pixels': MAX_PIXELS,
        'max_dimension': MAX_DIMENSION,
    }
