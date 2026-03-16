import os
import sys
from pathlib import Path

LEGACY_ID = 'youtube_downloader'
LEGACY_SCOPE = 'background'

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from runtime_bootstrap import resolve_shared_runtime
LEGACY_ROOT = APP_ROOT.parent / "_engine"
os.chdir(LEGACY_ROOT)
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
        _show_dependency_error(f"PySide6 is required to run this app.\n\n{exc}")
        return
    start_app(targets)


def main():
    _run_qt([])


if __name__ == "__main__":
    main()
