import os
import sys
from pathlib import Path

# Standard Contexthub Path Resolution
APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

def main():
    abs_app_root = APP_ROOT
    os.environ["CTX_APP_ROOT"] = str(abs_app_root)
    
    # Shared Runtime Path
    shared_root, shared_pkg_root = resolve_shared_runtime(abs_app_root)
    engine_path = abs_app_root.parent / "_engine"
    
    # Set CWD to engine
    if engine_path.exists():
        os.chdir(str(engine_path))
    
    for path in (engine_path, shared_root, shared_pkg_root):
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))

    # QT Launch
    from features.image.image_compare_qt_app import main as qt_main
    qt_main()

if __name__ == "__main__":
    main()
