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
        package_root_str = str(package_root)
        package_parent_str = str(package_parent)
        if package_parent_str not in sys.path:
            sys.path.insert(0, package_parent_str)
        if package_root_str not in sys.path:
            sys.path.insert(0, package_root_str)
        return

_setup_shims()

try:
    from contexthub.utils.gui_lib import *
except ImportError as e:
    print(f"Shim Error (gui_lib): {e}")
