import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.resolve().parents[1]
# Add category engine to sys.path
LEGACY_ROOT = APP_ROOT.parent / "_engine"
if str(LEGACY_ROOT) not in sys.path:
    sys.path.insert(0, str(LEGACY_ROOT))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Ensure Shared runtime is in path and takes precedence for internal shell imports
from runtime_bootstrap import resolve_shared_runtime
SHARED_PATH, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)

# Prepend in reverse order to ensure contexthub root is at the very top
for path in (SHARED_PATH, SHARED_PACKAGE_ROOT):
    path_str = str(path)
    if path.exists():
        if path_str in sys.path:
            sys.path.remove(path_str)
        sys.path.insert(0, path_str)

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
