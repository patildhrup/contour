"""Image decoding and tracing; invoked in a disposable, time-limited process."""
import io
import warnings
import xml.etree.ElementTree as ET

from PIL import Image, ImageOps, UnidentifiedImageError
import vtracer

from backend.config import MAX_PIXELS, MAX_DIMENSION, MAX_SVG_BYTES
from backend.services.preprocess import prepare

MIMES = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}


class ImageError(ValueError):
    pass


def decode(data: bytes, mime: str) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in MIMES or MIMES[image.format] != mime:
                    raise ImageError('The file contents do not match a supported PNG, JPEG or WebP image.')
                if image.width * image.height > MAX_PIXELS or max(image.size) > MAX_DIMENSION:
                    raise ImageError(f'Image exceeds the {MAX_PIXELS:,} pixel or {MAX_DIMENSION}px side limit.')
                if getattr(image, 'n_frames', 1) > 1:
                    raise ImageError('Animated images are not supported. Export a single frame first.')
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                return ImageOps.exif_transpose(image).convert('RGBA')
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageError('This image is damaged or cannot be decoded safely. Please export it again.') from exc


def _int_setting(settings: dict, key: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(settings.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def _trace_params(settings: dict, scale: int) -> dict:
    smoothing = _int_setting(settings, 'smoothing', 1, 0, 2)
    detail = _int_setting(settings, 'detail', 2, 1, 3)
    speckle = _int_setting(settings, 'speckle', 4, 0, 64)
    corner = _int_setting(settings, 'corner', 1, 0, 2)
    simplify = _int_setting(settings, 'simplify', 0, 0, 2)
    colors = _int_setting(settings, 'colors', 16, 2, 64)

    # Adaptive color precision and layer separation to eliminate fringe halos around edges:
    if colors <= 8:
        color_precision = 4
        layer_difference = 36
    elif colors <= 16:
        color_precision = 5
        layer_difference = 28
    elif colors <= 32:
        color_precision = 6
        layer_difference = 20
    else:
        color_precision = 6
        layer_difference = 16

    if 'color_precision' in settings:
        color_precision = _int_setting(settings, 'color_precision', color_precision, 1, 8)

    filter_speckle = max(4, speckle * 2)

    # Corner threshold:
    # 55-65 keeps acute corners sharp (like hair spikes or logo points),
    # while rounding off 90-degree pixel staircases.
    corner_threshold = {0: 45, 1: 58, 2: 75}[corner]
    if smoothing == 2:
        corner_threshold = max(35, corner_threshold - 10)

    # Length threshold:
    # Controls curve segment length. Higher values produce longer, smoother sweeping curves.
    length_threshold = {1: 7.0, 2: 5.5, 3: 4.0}[detail]
    if simplify == 1:
        length_threshold += 1.0
    elif simplify == 2:
        length_threshold += 2.5

    splice_threshold = {0: 40, 1: 45, 2: 55}[smoothing]

    return {
        'colormode': 'color',
        'hierarchical': 'stacked',
        'mode': 'polygon' if smoothing == 0 else 'spline',
        'filter_speckle': filter_speckle,
        'color_precision': color_precision,
        'layer_difference': layer_difference,
        'corner_threshold': corner_threshold,
        'length_threshold': length_threshold,
        'max_iterations': 20,
        'splice_threshold': splice_threshold,
        'path_precision': 4,
    }


def _fit_svg_to_original(svg: str, traced_size: tuple[int, int], original_size: tuple[int, int]) -> ET.Element:
    root = ET.fromstring(svg)
    traced_w, traced_h = traced_size
    orig_w, orig_h = original_size
    if traced_size != original_size and traced_w and traced_h:
        sx, sy = orig_w / traced_w, orig_h / traced_h
        group = ET.Element('g')
        group.set('transform', f'scale({sx:.8f} {sy:.8f})')
        for child in list(root):
            root.remove(child)
            group.append(child)
        root.append(group)
    root.set('width', str(orig_w))
    root.set('height', str(orig_h))
    root.set('viewBox', f'0 0 {orig_w} {orig_h}')
    return root


def trace(data: bytes, mime: str, settings: dict) -> dict:
    image = decode(data, mime)
    prepared = prepare(image, settings)
    notices = list(prepared.notices)
    width, height = prepared.image.size
    if prepared.image.getchannel('A').getextrema()[1] == 0:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{image.width}" height="{image.height}" '
            f'viewBox="0 0 {image.width} {image.height}" />'
        )
        root = ET.fromstring(svg)
    else:
        buffer = io.BytesIO()
        prepared.image.save(buffer, format='PNG')
        svg = vtracer.convert_raw_image_to_svg(
            buffer.getvalue(),
            img_format='png',
            **_trace_params(settings, prepared.scale),
        )
        root = _fit_svg_to_original(svg, (width, height), prepared.original_size)
    if len(ET.tostring(root, encoding='unicode').encode()) > MAX_SVG_BYTES:
        raise ImageError('The vector is too complex. Try fewer colors, less detail or more noise filtering.')
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    svg = ET.tostring(root, encoding='unicode')
    paths = sum(1 for item in root.iter() if item.tag.endswith('}path'))
    return {
        'svg': svg,
        'width': prepared.original_size[0],
        'height': prepared.original_size[1],
        'paths': paths,
        'warnings': notices,
    }
