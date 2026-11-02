import os
from dotenv import load_dotenv

load_dotenv()
MAX_UPLOAD_BYTES = int(os.getenv('MAX_UPLOAD_BYTES', '10485760'))
MAX_PIXELS = int(os.getenv('MAX_PIXELS', '4000000'))
MAX_DIMENSION = int(os.getenv('MAX_DIMENSION', '4096'))
CONVERSION_TIMEOUT = int(os.getenv('CONVERSION_TIMEOUT', '60'))
MAX_CONCURRENT = int(os.getenv('MAX_CONCURRENT', '2'))
MAX_SVG_BYTES = int(os.getenv('MAX_SVG_BYTES', '20971520'))
CORS_ORIGINS = [x.strip() for x in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()]

