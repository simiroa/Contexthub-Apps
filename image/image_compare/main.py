import os
import sys
import time
from pathlib import Path

_T0 = time.perf_counter()


def _log_startup(label: str) -> None:
    if os.environ.get("CTX_STARTUP_TRACE"):
        print(f"[startup] {label} t+{(time.perf_counter() - _T0) * 1000:.0f}ms", file=sys.stderr)


# Standard Contexthub Path Resolution
APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

engine_path = APP_ROOT.parent / "_engine"
shared_root, shared_pkg_root = resolve_shared_runtime(APP_ROOT)
for path in (engine_path, shared_root, shared_pkg_root):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

def main():
    _log_startup("entering main")
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

    # Handle targets
    targets = [a for a in sys.argv[1:] if a and not a.startswith("-")]

    from features.image.image_compare_qt_app import start_app
    _log_startup("qt_app imported")
    sys.exit(start_app(targets))

if __name__ == "__main__":
    main()
