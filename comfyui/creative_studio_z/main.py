import os
import sys
from pathlib import Path


LEGACY_ID = "creative_studio_z"
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


def _show_dependency_error(message: str) -> None:
    print(message, file=sys.stderr)


def main():
    from utils.i18n import load_extra_strings

    loc_file = LEGACY_ROOT / "locales.json"
    if loc_file.exists():
        load_extra_strings(loc_file)
    try:
        from features.comfyui.creative_studio_z_qt_app import start_app
    except ImportError as exc:
        _show_dependency_error(format_startup_error(exc))
        return

    start_app([])


if __name__ == "__main__":
    main()
