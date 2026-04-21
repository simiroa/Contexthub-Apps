import os
import sys
from pathlib import Path

APP_ID = "versus_up"
APP_TITLE = "VersusUp"
LEGACY_SCOPE = "standalone"

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LEGACY_ROOT = APP_ROOT.parent / "_engine"
from runtime_bootstrap import resolve_shared_runtime

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (LEGACY_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)

feature_dir = LEGACY_ROOT / "features" / APP_ID
if feature_dir.exists() and str(feature_dir) not in sys.path:
    sys.path.insert(0, str(feature_dir))

os.environ.setdefault("CTX_APP_ROOT", str(APP_ROOT))

from contexthub.utils.startup_errors import format_startup_error


def _show_dependency_error(message: str) -> None:
    print(message, file=sys.stderr)


def main() -> None:
    from utils.i18n import load_extra_strings

    locale_file = LEGACY_ROOT / "locales.json"
    if locale_file.exists():
        load_extra_strings(locale_file)
    try:
        from features.versus_up.versus_up_qt_app import start_app
    except ImportError as exc:
        _show_dependency_error(format_startup_error(exc))
        return

    start_app([])


if __name__ == "__main__":
    main()
