import os
import sys
from pathlib import Path

LEGACY_ID = 'doc_convert'
LEGACY_SCOPE = 'file'

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from runtime_bootstrap import resolve_shared_runtime
from contexthub.utils.startup_errors import format_startup_error
LEGACY_ROOT = APP_ROOT.parent / "_engine"
sys.path.insert(0, str(LEGACY_ROOT))
if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

# Ensure Shared runtime is in path for i18n and shared UI/runtime modules
SHARED_PATH, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (SHARED_PATH, SHARED_PACKAGE_ROOT):
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)

try:
    from utils.i18n import load_extra_strings
    loc_file = LEGACY_ROOT / "locales.json"
    if loc_file.exists():
        load_extra_strings(loc_file)
except Exception:
    pass


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


def _show_dependency_error(message: str) -> None:
    print(message, file=sys.stderr)


def _run_qt(targets) -> None:
    try:
        from features.document.doc_convert_qt_app import start_app
    except ImportError as exc:
        _show_dependency_error(format_startup_error(exc))
        return
    start_app(targets)


def main():
    targets = _pick_targets()
    _run_qt(targets)


if __name__ == "__main__":
    main()
