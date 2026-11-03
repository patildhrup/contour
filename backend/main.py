import backend  # noqa: F401 - Initializes sys.path for local venv
from importlib.metadata import version
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.config import CORS_ORIGINS, MAX_UPLOAD_BYTES, MAX_PIXELS, MAX_DIMENSION
from backend.routes.convert import router


class BodyLimit:
    """Bound the complete multipart body before Starlette parses or spools it."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        if scope['method'] == 'POST':
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body.extend(message.get('body', b''))
                if len(body) > MAX_UPLOAD_BYTES + 65536:
                    return await JSONResponse({'detail': 'Upload exceeds the size limit.'}, status_code=413)(scope, receive, send)
                if not message.get('more_body'):
                    break
            delivered = False
            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()
            return await self.app(scope, replay, send)
        return await self.app(scope, receive, send)


app = FastAPI(title='Contour API', version='1.0.0')
app.include_router(router, prefix='/api')
app.add_middleware(BodyLimit)
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
    try:
        engine_version = version('vtracer')
        engine_ok = True
    except Exception:
        engine_version = 'unavailable'
        engine_ok = False
    return {
        'status': 'ok',
        'engine': f'vtracer {engine_version}',
        'engine_ok': engine_ok,
        'max_upload_bytes': MAX_UPLOAD_BYTES,
        'max_pixels': MAX_PIXELS,
        'max_dimension': MAX_DIMENSION,
    }
