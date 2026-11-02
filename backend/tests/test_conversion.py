import io
import xml.etree.ElementTree as ET
import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.tracing import trace

client = TestClient(app)
DEFAULTS = dict(
    mode='color', colors=8, color_precision=8, smoothing=1, detail=2,
    speckle=0, corner=1, simplify=0, remove_background=False,
)


def fixture_image(fmt='PNG', transparent=False):
    image = Image.new('RGBA' if transparent else 'RGB', (80, 64), (0, 0, 0, 0) if transparent else 'white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 35, 50), fill='red')
    draw.ellipse((40, 12, 72, 48), fill='blue')
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.mark.parametrize('fmt,mime', [('PNG','image/png'), ('JPEG','image/jpeg'), ('WEBP','image/webp')])
def test_real_paths_for_each_format(fmt, mime):
    response = client.post('/api/convert', files={'file': ('../../unsafe.png', fixture_image(fmt), mime)})
    assert response.status_code == 200, response.text
    result = response.json()
    root = ET.fromstring(result['svg'])
    assert result['paths'] >= 2
    assert root.attrib['viewBox'] == '0 0 80 64'
    assert not any(el.tag.endswith('image') for el in root.iter())
    assert result['filename'] == 'unsafe-contour.svg'
    assert len(result['id']) == 32


def test_transparency_and_palette_are_real():
    result = trace(fixture_image(transparent=True), 'image/png', DEFAULTS)
    fills = {el.attrib.get('fill', '').lower() for el in ET.fromstring(result['svg']).iter() if el.tag.endswith('path')}
    assert '#ff0000' in fills and '#0000ff' in fills
    assert '#000000' not in fills


def test_monochrome_and_background_removal():
    result = trace(fixture_image(), 'image/png', {**DEFAULTS, 'mode':'monochrome', 'remove_background':True})
    fills = {el.attrib.get('fill', '').lower() for el in ET.fromstring(result['svg']).iter() if el.tag.endswith('path')}
    assert fills == {'#000000'}


def test_all_transparent_is_valid_empty_svg():
    buf = io.BytesIO()
    Image.new('RGBA', (30,30)).save(buf, format='PNG')
    result = trace(buf.getvalue(), 'image/png', DEFAULTS)
    assert result['paths'] == 0 and result['warnings']
    ET.fromstring(result['svg'])


@pytest.mark.parametrize('body,mime,status', [(b'not image','image/png',422), (b'<svg/>','image/svg+xml',415), (b'','image/png',422), (fixture_image(),'image/jpeg',422)])
def test_rejects_malformed_and_spoofed_uploads(body,mime,status):
    response = client.post('/api/convert', files={'file': ('x.png',body,mime)})
    assert response.status_code == status
    assert 'Traceback' not in response.text


def test_invalid_setting():
    response = client.post('/api/convert', files={'file': ('x.png',fixture_image(),'image/png')}, data={'colors':'9999'})
    assert response.status_code == 422


def test_rejects_dimensions():
    buf=io.BytesIO()
    Image.new('RGB',(4097,1)).save(buf,format='PNG')
    response=client.post('/api/convert',files={'file':('wide.png',buf.getvalue(),'image/png')})
    assert response.status_code == 422 and 'limit' in response.json()['detail']


def test_rejects_oversized_body():
    from backend.config import MAX_UPLOAD_BYTES
    response=client.post('/api/convert',content=b'x'*(MAX_UPLOAD_BYTES+65537),headers={'content-type':'application/octet-stream'})
    assert response.status_code == 413


def test_health_and_cors():
    response=client.get('/api/health',headers={'Origin':'http://localhost:5173'})
    assert response.status_code == 200
    assert response.json()['engine'].startswith('vtracer')
    assert response.headers['access-control-allow-origin']=='http://localhost:5173'
    assert response.headers['cache-control']=='no-store'


def test_settings_change_output():
    pixels=fixture_image()
    sharp=trace(pixels,'image/png',{**DEFAULTS,'smoothing':0})['svg']
    smooth=trace(pixels,'image/png',DEFAULTS)['svg']
    assert sharp != smooth


def test_advanced_settings_are_applied():
    response = client.post(
        '/api/convert',
        files={'file': ('x.png', fixture_image(), 'image/png')},
        data={'corner': '2', 'simplify': '2', 'color_precision': '6', 'speckle': '8'},
    )
    assert response.status_code == 200
    assert response.json()['paths'] >= 2
    assert response.json()['width'] == 80


def test_output_keeps_original_dimensions_after_upscale():
    result = trace(fixture_image(), 'image/png', {**DEFAULTS, 'detail': 3})
    assert result['width'] == 80 and result['height'] == 64
    root = ET.fromstring(result['svg'])
    assert root.attrib['viewBox'] == '0 0 80 64'
    assert result['paths'] >= 2


def test_animated_input_rejected():
    buf=io.BytesIO()
    Image.new('RGB',(20,20),'red').save(buf,format='WEBP',save_all=True,append_images=[Image.new('RGB',(20,20),'blue')],duration=100,loop=0)
    response=client.post('/api/convert',files={'file':('animated.webp',buf.getvalue(),'image/webp')})
    assert response.status_code == 422 and 'Animated' in response.json()['detail']


def test_timeout_kills_worker_and_cleans_temporary_files(monkeypatch):
    import asyncio
    import importlib
    from pathlib import Path
    module=importlib.import_module('backend.routes.convert')
    paths=[]
    class SlowProcess:
        returncode=None
        killed=False
        async def wait(self):
            if not self.killed:
                await asyncio.sleep(5)
            self.returncode=-1
        def kill(self):
            self.killed=True
    process=SlowProcess()
    async def create(*args,**kwargs):
        paths.append(Path(args[-1]))
        return process
    monkeypatch.setattr(module.asyncio,'create_subprocess_exec',create)
    monkeypatch.setattr(module,'CONVERSION_TIMEOUT',0.01)
    response=client.post('/api/convert',files={'file':('test.png',fixture_image(),'image/png')})
    assert response.status_code == 504
    assert process.killed
    assert paths and not paths[0].exists()


def test_busy_returns_retryable_error(monkeypatch):
    import asyncio
    import importlib
    module=importlib.import_module('backend.routes.convert')
    monkeypatch.setattr(module,'slots',asyncio.Semaphore(0))
    response=client.post('/api/convert',files={'file':('test.png',fixture_image(),'image/png')})
    assert response.status_code == 429 and response.headers['retry-after']=='3'


def test_not_implemented_fallback_executes_successfully(monkeypatch):
    import importlib
    module = importlib.import_module('backend.routes.convert')

    async def raise_not_implemented(*args, **kwargs):
        raise NotImplementedError

    monkeypatch.setattr(module.asyncio, 'create_subprocess_exec', raise_not_implemented)
    response = client.post('/api/convert', files={'file': ('test.png', fixture_image(), 'image/png')})
    assert response.status_code == 200
    result = response.json()
    assert result['paths'] >= 2
    assert result['filename'] == 'test-contour.svg'


def test_not_implemented_fallback_timeout(monkeypatch):
    import importlib
    module = importlib.import_module('backend.routes.convert')

    async def raise_not_implemented(*args, **kwargs):
        raise NotImplementedError

    monkeypatch.setattr(module.asyncio, 'create_subprocess_exec', raise_not_implemented)
    monkeypatch.setattr(module, 'CONVERSION_TIMEOUT', 0.0001)
    response = client.post('/api/convert', files={'file': ('test.png', fixture_image(), 'image/png')})
    assert response.status_code == 504


