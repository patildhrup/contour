"""Private worker entrypoint. Only trusted server-generated paths reach this module."""
import json
import logging
import sys
import traceback
from pathlib import Path

from backend.services.tracing import ImageError, trace

if __name__ == '__main__':
    directory = Path(sys.argv[1])
    try:
        request = json.loads((directory / 'request.json').read_text(encoding='utf-8'))
        result = trace((directory / 'input').read_bytes(), request['mime'], request['settings'])
    except ImageError as exc:
        result = {'error': str(exc)}
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        result = {'error': f'The tracing engine could not process this image: {str(exc)}'}
    (directory / 'result.json').write_text(json.dumps(result), encoding='utf-8')

