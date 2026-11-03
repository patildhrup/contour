import os
import sys

# Ensure local virtual environment packages are accessible
# even if uvicorn is launched with the base/system Python interpreter.
_venv_site_packages = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".venv", "Lib", "site-packages")
)
if os.path.isdir(_venv_site_packages) and _venv_site_packages not in sys.path:
    sys.path.insert(0, _venv_site_packages)
