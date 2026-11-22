"""Guard against serverless dependency drift that breaks /api/convert.

/api/health stays green when tracing imports are missing, so the failure only
shows up as a 500 during conversion. Vercel installs only the requirements.txt
next to api/index.py; this test keeps that file aligned with the engine.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_REQUIREMENTS = ROOT / 'backend' / 'requirements.txt'
API_REQUIREMENTS = ROOT / 'backend' / 'api' / 'requirements.txt'

# Third-party packages imported by the conversion path (tracing, OpenCV stage,
# VTracer core, StarVector/SAM HTTP clients). A missing pin here means a 500
# on the deployed endpoint while health checks still pass.
CONVERSION_RUNTIME = {
    'fastapi', 'uvicorn', 'python-multipart', 'pillow', 'numpy',
    'python-dotenv', 'httpx', 'opencv-python-headless', 'vtracer',
}


def _pins(path: Path) -> dict[str, str]:
    pins = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        name, _, version = line.partition('==')
        pins[name.strip().lower()] = version.strip()
    return pins


def test_serverless_requirements_include_conversion_runtime():
    pins = _pins(API_REQUIREMENTS)
    assert CONVERSION_RUNTIME <= set(pins), (
        f'Missing from api/requirements.txt: {sorted(CONVERSION_RUNTIME - set(pins))}'
    )
    assert all(pins[name] for name in CONVERSION_RUNTIME), 'Runtime pins must be versioned'


def test_serverless_pins_match_local_requirements():
    local = _pins(LOCAL_REQUIREMENTS)
    serverless = _pins(API_REQUIREMENTS)
    shared = set(local) & set(serverless)
    assert shared, 'No shared dependencies to compare'
    assert {name: local[name] for name in shared} == {name: serverless[name] for name in shared}
