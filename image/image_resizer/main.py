import os
import sys
from pathlib import Path

APP_ID = 'image_resizer'
APP_SCOPE = 'file'

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from runtime_bootstrap import resolve_shared_runtime
LEGACY_ROOT = APP_ROOT.parent / "_engine"
SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (LEGACY_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)
if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)


def _capture_mode():
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"

def _pick_targets():
    if APP_SCOPE in {"background", "tray_only", "standalone"}:
        return []

    if _capture_mode():
        try:
            from utils.headless_inputs import get_headless_targets
            return get_headless_targets(APP_ID, APP_SCOPE, LEGACY_ROOT)
        except Exception:
            return []

    args = [a for a in sys.argv[1:] if a]
    if args:
        return args
    return []


def _run_qt(targets):
    try:
        from features.image.image_resizer_qt_app import start_app
        start_app(targets)
    except ImportError as e:
        print(f"Failed to load Qt app: {e}")
        raise e


def main():
    targets = _pick_targets()
    _run_qt(targets)


if __name__ == "__main__":
    main()
