import sys
import os
from pathlib import Path

def _setup_shims():
    candidates = []
    env_shared_root = os.environ.get("CTX_SHARED_ROOT")
    if env_shared_root:
        candidates.append(Path(env_shared_root))
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        candidates.append(parent / "dev-tools" / "runtime" / "Shared" / "contexthub")
        candidates.append(parent / "Runtimes" / "Shared" / "contexthub")
    for package_root in candidates:
        if not package_root.exists():
            continue
        package_parent = package_root.parent
        if str(package_parent) not in sys.path:
            sys.path.insert(0, str(package_parent))
        if str(package_root) not in sys.path:
            sys.path.insert(0, str(package_root))
        return

_setup_shims()

try:
    from contexthub.utils.ai_runner import *
except ImportError:
    pass
