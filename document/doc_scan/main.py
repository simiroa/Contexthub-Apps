import os
import sys
from pathlib import Path

LEGACY_ID = "doc_scan"
LEGACY_SCOPE = "file"

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

LEGACY_ROOT = APP_ROOT.parent / "_engine"
for path in (LEGACY_ROOT,):
    if path.exists():
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

SHARED_PATH, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (SHARED_PATH, SHARED_PACKAGE_ROOT):
    if path.exists():
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

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
    from features.document.doc_scan_qt_app import start_app
    start_app(targets)

def main():
    try:
        from utils.i18n import load_extra_strings

        loc_file = LEGACY_ROOT / "locales.json"
        if loc_file.exists():
            load_extra_strings(loc_file)
    except Exception:
        pass

    targets = _pick_targets()
    _run_qt(targets)

if __name__ == "__main__":
    main()
