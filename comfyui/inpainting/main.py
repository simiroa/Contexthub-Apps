import os
import sys
from pathlib import Path


LEGACY_ID = "inpainting"
LEGACY_SCOPE = ""

APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"
REPO_ROOT = APP_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime
from contexthub.utils.startup_errors import format_startup_error

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for entry in (LEGACY_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if entry.exists():
        entry_str = str(entry)
        if entry_str not in sys.path:
            sys.path.insert(0, entry_str)

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

    return [arg for arg in sys.argv[1:] if arg]


def _show_dependency_error(message: str) -> None:
    print(message, file=sys.stderr)


def main():
    from utils.i18n import load_extra_strings
    loc_file = LEGACY_ROOT / "locales.json"
    if loc_file.exists():
        load_extra_strings(loc_file)
    try:
        from features.comfyui.inpainting_qt_app import start_app
    except ImportError as exc:
        _show_dependency_error(format_startup_error(exc))
        return

    start_app(_pick_targets())


if __name__ == "__main__":
    main()
