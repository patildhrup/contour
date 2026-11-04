import sys
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parents[1]

# When the Vercel project's Root Directory is the repo root, the parent of
# this package (the repo root) is already importable and nothing to do here.
if (_pkg_dir.parent / "backend").is_dir() and str(_pkg_dir.parent) not in sys.path:
    sys.path.insert(0, str(_pkg_dir.parent))

# Fallback: if the Root Directory points straight at backend/ (so this package
# is deployed as "api/" at the project root), re-register this directory under
# the name "backend" so the codebase's absolute `backend.*` imports keep
# working without any code changes.
if "backend" not in sys.modules and not (_pkg_dir.parent / "backend").is_dir():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "backend", _pkg_dir / "__init__.py", submodule_search_locations=[str(_pkg_dir)]
    )
    pkg = importlib.util.module_from_spec(spec)
    sys.modules["backend"] = pkg
    spec.loader.exec_module(pkg)
