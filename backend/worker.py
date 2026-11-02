"""Private worker entrypoint. Only trusted server-generated paths reach this module."""
import json
import sys
from pathlib import Path
from backend.services.tracing import ImageError, trace

if __name__ == '__main__':
    directory = Path(sys.argv[1])
    try:
        request = json.loads((directory / 'request.json').read_text())
        result = trace((directory / 'input').read_bytes(), request['mime'], request['settings'])
    except ImageError as exc:
        result = {'error': str(exc)}
    except Exception:
        result = {'error': 'The tracing engine could not process this image. Try a simpler image or different settings.'}
    (directory / 'result.json').write_text(json.dumps(result), encoding='utf-8')

