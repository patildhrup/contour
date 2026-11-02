"""Reproducible, original demo artwork plus actual VTracer result."""
import io
import math
from pathlib import Path
from PIL import Image, ImageDraw
from backend.services.tracing import trace

def main():
    directory = Path(__file__).resolve().parents[1] / 'frontend' / 'public' / 'demo'
    directory.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGB', (720, 720), '#efe9dc')
    draw = ImageDraw.Draw(image)
    for petal in range(8):
        angle = petal * math.pi / 4
        points = []
        for i in range(100):
            t = i * 2 * math.pi / 100
            x, y = 67 * math.cos(t), -135 + 143 * math.sin(t)
            points.append((360 + x * math.cos(angle) - y * math.sin(angle), 360 + x * math.sin(angle) + y * math.cos(angle)))
        draw.polygon(points, fill='#f0502b' if petal % 2 else '#232c29')
    draw.ellipse((299,299,421,421), fill='#efe9dc')
    # Low-resolution input deliberately shows why paths help at larger display sizes.
    image = image.resize((180,180), Image.Resampling.LANCZOS)
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    (directory / 'flower.png').write_bytes(stream.getvalue())
    result = trace(stream.getvalue(), 'image/png', dict(mode='color',colors=3,smoothing=1,detail=3,speckle=4,remove_background=False))
    (directory / 'flower.svg').write_text(result['svg'], encoding='utf-8')
    print(f'Original demo: {result["paths"]} actual vector paths')

if __name__ == '__main__':
    main()
