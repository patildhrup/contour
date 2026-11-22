import os
from pathlib import Path
from dotenv import load_dotenv

# Load the .env that lives beside this module first (so running uvicorn from
# the repo root still picks up backend/.env), then fall back to the CWD walk.
load_dotenv(Path(__file__).resolve().parent / '.env')
load_dotenv()
MAX_UPLOAD_BYTES = int(os.getenv('MAX_UPLOAD_BYTES', '20971520'))  # 20 MB
MAX_PIXELS = int(os.getenv('MAX_PIXELS', '6000000'))  # ~3 megapixels
MAX_DIMENSION = int(os.getenv('MAX_DIMENSION', '4096'))
CONVERSION_TIMEOUT = int(os.getenv('CONVERSION_TIMEOUT', '60'))
MAX_CONCURRENT = int(os.getenv('MAX_CONCURRENT', '2'))
MAX_SVG_BYTES = int(os.getenv('MAX_SVG_BYTES', '20971520'))
# Images larger than this are traced at reduced resolution (results are scaled
# back to original dimensions), bounding subpixel tracing time.
TRACE_PIXEL_BUDGET = int(os.getenv('TRACE_PIXEL_BUDGET', '1600000'))

# StarVector-1B and SAM 2 AI pipeline configuration
HUGGINGFACE_API_KEY = (
    os.getenv('HUGGINGFACE_API_KEY')
    or os.getenv('HUGGINGFACE_ACCESS_TOKEN')
    or os.getenv('HF_TOKEN')
    or ''
).strip().strip('"').strip("'")
STARVECTOR_MODEL_ID = os.getenv('STARVECTOR_MODEL_ID', 'starvector/starvector-1b-im2svg')
STARVECTOR_ENDPOINT = os.getenv('STARVECTOR_ENDPOINT', '')
SAM2_ENDPOINT = os.getenv('SAM2_ENDPOINT', '')
DEFAULT_ENGINE = os.getenv('DEFAULT_ENGINE', 'hybrid')

DEFAULT_ORIGINS = (
    'http://localhost:5173,http://127.0.0.1:5173,'
    'http://localhost:8000,http://127.0.0.1:8000,'
    'http://localhost:8080,http://127.0.0.1:8080,'
    'http://localhost:8081,http://127.0.0.1:8081,'
    'https://contour-black.vercel.app'
)
CORS_ORIGINS = [x.strip() for x in os.getenv('CORS_ORIGINS', DEFAULT_ORIGINS).split(',') if x.strip()]
