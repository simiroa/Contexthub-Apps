import os
import sys
from pathlib import Path

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
    abs_app_root = APP_ROOT
    os.environ["CTX_APP_ROOT"] = str(abs_app_root)

    from features.image.image_compare_qt_app import main as qt_main
    qt_main()

if __name__ == "__main__":
    main()
