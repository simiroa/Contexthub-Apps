import os
from pathlib import Path

_shared_root = os.environ.get("CTX_SHARED_ROOT")
if not _shared_root:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        candidate = parent / "Runtimes" / "Shared" / "contexthub"
        if candidate.exists():
            _shared_root = str(candidate)
            break

if _shared_root:
    shared_utils = Path(_shared_root) / "utils"
    if shared_utils.exists():
        shared_path = str(shared_utils)
        if shared_path not in __path__:
            __path__.append(shared_path)
