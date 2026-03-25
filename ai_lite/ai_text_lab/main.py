import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent

REPO_ROOT = APP_ROOT.parents[1]
LEGACY_ROOT = APP_ROOT.parent / "_engine"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
FEATURE_DIR = LEGACY_ROOT / "features" / "tools"
for path in (LEGACY_ROOT, FEATURE_DIR, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if path.exists():
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

def main():
    # Now import app components
    try:
        from ai_text_lab_qt_app import start_app
        sys.exit(start_app())
    except Exception as e:
        print(f"Failed to start AI Text Lab: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
