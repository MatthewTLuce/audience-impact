"""Fixed parser child; input bytes are data, never executable arguments."""
import json
import sys
import resource
from .ingest import extract, MAX_BYTES
from .domain import BoundaryError

def main():
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    try:
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    except (ValueError, OSError):
        pass  # Some macOS builds do not implement an address-space limit.
    try:
        text = extract(sys.stdin.buffer.read(MAX_BYTES+1), sys.argv[1])
        print(json.dumps(dict(text=text)))
    except (BoundaryError, MemoryError) as exc:
        print(json.dumps(dict(error=str(exc) if isinstance(exc,BoundaryError) else 'parser memory limit')))
        return 2
    return 0

if __name__=='__main__':
    raise SystemExit(main())
