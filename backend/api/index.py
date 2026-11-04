# Vercel serverless entrypoint. Vercel's resolver imports this file by path
# (importlib.util.spec_from_file_location), which never executes api/__init__.py
# and may not expose the repo layout on sys.path. So the bootstrap that makes
# the backend's absolute `backend.*` imports work is inlined here. It handles
# both possible Root Directory settings: repo root and backend/.
import importlib.util
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_pkg_dir = _here.parent  # the backend/ directory itself


def _bootstrap():
    # Scenario A: whole repo deployed; make the repo root importable so the
    # real `backend` package resolves normally.
    if (_pkg_dir / "main.py").is_file():
        for candidate in (_pkg_dir.parent, _pkg_dir):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
        if (_pkg_dir.parent / "backend").is_dir() or "backend" in sys.modules:
            return
    # Scenario B: Root Directory is backend/ (or its parent is not importable):
    # register the backend directory as the `backend` package explicitly.
    if "backend" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "backend", _pkg_dir / "__init__.py",
            submodule_search_locations=[str(_pkg_dir)],
        )
        pkg = importlib.util.module_from_spec(spec)
        sys.modules["backend"] = pkg
        spec.loader.exec_module(pkg)


_bootstrap()

from backend.main import app  # noqa: E402
