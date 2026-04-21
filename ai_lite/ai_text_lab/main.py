import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent

REPO_ROOT = APP_ROOT.parents[1]
LEGACY_ROOT = APP_ROOT.parent / "_engine"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime
from contexthub.utils.startup_errors import format_startup_error

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
    try:
        from ai_text_lab_qt_app import start_app
    except Exception as exc:
        print(f"AI Text Lab startup failed: {format_startup_error(exc)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    return start_app()

if __name__ == "__main__":
    raise SystemExit(main())
