import os
import sys
from pathlib import Path

LEGACY_ID = 'rigreader_vectorizer'
LEGACY_SCOPE = 'file'

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
    if LEGACY_SCOPE in {"background", "tray_only", "standalone"}:
        return []

    if _capture_mode():
        try:
            from utils.headless_inputs import get_headless_targets
            return get_headless_targets(LEGACY_ID, LEGACY_SCOPE, LEGACY_ROOT)
        except Exception:
            return []

    args = [a for a in sys.argv[1:] if a]
    if args:
        return args
    return []


def _run_qt(targets):
    from features.image.vectorizer.rigreader_vectorizer_qt_app import start_app
    start_app(targets)


def main():
    targets = _pick_targets()
    # For Qt, we allow starting without targets to show the workspace
    _run_qt(targets)


if __name__ == "__main__":
    main()
