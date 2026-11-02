import sys
from pathlib import Path

# Legacy entrypoint: backend imports require the repository root, not backend/.
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.main import app

