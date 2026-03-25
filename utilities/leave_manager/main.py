import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
LEGACY_ROOT = APP_ROOT.parent / "_engine"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

os.chdir(LEGACY_ROOT)
SHARED_PATH, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (SHARED_PATH, SHARED_PACKAGE_ROOT):
    if path.exists():
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

if LEGACY_ROOT.exists() and str(LEGACY_ROOT) not in sys.path:
    sys.path.insert(0, str(LEGACY_ROOT))

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

# Load i18n
try:
    from contexthub.utils.i18n import t as _t_check
    from utils.i18n import load_extra_strings
    load_extra_strings(LEGACY_ROOT / "locales.json")
except Exception:
    pass


def _capture_mode():
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"


def main():
    if _capture_mode():
        return

    from features.leave_manager.leave_manager_qt_app import start_app
    start_app([])


if __name__ == "__main__":
    main()
