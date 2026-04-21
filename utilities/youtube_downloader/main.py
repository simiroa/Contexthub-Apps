import os
import sys
from pathlib import Path

LEGACY_ID = 'youtube_downloader'
LEGACY_SCOPE = 'background'

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime
from contexthub.utils.startup_errors import format_startup_error
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

try:
    from utils.i18n import load_extra_strings
    load_extra_strings(LEGACY_ROOT / "locales.json")
except Exception:
    pass


def _capture_mode():
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"


def _show_dependency_error(message: str) -> None:
    print(message, file=sys.stderr)


def _run_qt(targets) -> None:
    try:
        from features.video.youtube_downloader_qt_app import start_app
    except ImportError as exc:
        _show_dependency_error(format_startup_error(exc))
        return
    start_app(targets)


def main():
    _run_qt([])


if __name__ == "__main__":
    main()
