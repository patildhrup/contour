import os
from dotenv import load_dotenv

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

DEFAULT_ORIGINS = (
    'http://localhost:5173,http://127.0.0.1:5173,'
    'http://localhost:8080,http://127.0.0.1:8080,'
    'http://localhost:8081,http://127.0.0.1:8081,'
    'https://contour-black.vercel.app'
)
CORS_ORIGINS = [x.strip() for x in os.getenv('CORS_ORIGINS', DEFAULT_ORIGINS).split(',') if x.strip()]
