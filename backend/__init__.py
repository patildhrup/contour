import os
import sys

# Ensure local virtual environment packages are accessible
# even if uvicorn is launched with the base/system Python interpreter.
for _candidate in (
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".venv", "Lib", "site-packages")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "Lib", "site-packages")),
):
    if os.path.isdir(_candidate) and _candidate not in sys.path:
        sys.path.insert(0, _candidate)
