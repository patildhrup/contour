"""Exercise the deployed entrypoint without the checkout or its local path shim."""

import shutil
import subprocess
import sys
from pathlib import Path


def test_vercel_entrypoint_from_standalone_bundle(tmp_path):
    root = Path(__file__).resolve().parents[2]
    shutil.copy2(root / 'main.py', tmp_path / 'main.py')
    shutil.copytree(
        root / 'backend', tmp_path / 'backend',
        ignore=shutil.ignore_patterns('__pycache__', 'tests'),
    )
    script = '''
import io
import sys
from pathlib import Path

# Isolated Python omits cwd; Vercel adds the function bundle to the import path.
sys.path.insert(0, str(Path.cwd()))
from main import app
from fastapi.testclient import TestClient
from PIL import Image
import backend.services.tracing as tracing

def unexpected_fallback(*args, **kwargs):
    raise AssertionError('The packaged subprocess worker must handle conversion')

# Only the parent is patched: the worker imports its own tracing module.
tracing.trace = unexpected_fallback
with TestClient(app) as client:
    assert client.get('/').status_code == 200
    health = client.get('/api/health')
    assert health.status_code == 200, health.text
    assert health.json()['engine_ok'] is True
    response = client.options('/api/convert', headers={
        'Origin': 'https://contour-black.vercel.app',
        'Access-Control-Request-Method': 'POST',
    })
    assert response.status_code == 200, response.text
    assert response.headers['access-control-allow-origin'] == 'https://contour-black.vercel.app'
    image = io.BytesIO()
    Image.new('RGB', (32, 32), 'red').save(image, format='PNG')
    response = client.post('/api/convert', files={
        'file': ('deployment.png', image.getvalue(), 'image/png'),
    })
    assert response.status_code == 200, response.text
    assert response.json()['paths'] >= 1
print('Standalone entrypoint, health, CORS and subprocess conversion passed')
'''
    result = subprocess.run(
        [sys.executable, '-I', '-c', script], cwd=tmp_path,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
