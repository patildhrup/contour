# Vercel serverless entrypoint. The package's __init__ installs the sys.path /
# package aliases needed for the backend's absolute `backend.*` imports, no
# matter whether the Vercel Root Directory is the repo root or backend/.
from backend.main import app  # noqa: E402
