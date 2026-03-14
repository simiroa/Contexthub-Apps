import os
import sys
from pathlib import Path

LEGACY_ID = 'youtube_downloader'
LEGACY_SCOPE = 'background'

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"
os.chdir(LEGACY_ROOT)
sys.path.insert(0, str(LEGACY_ROOT))
if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

# Ensure Shared runtime is in path for i18n and Flet tokens
SHARED_PATH = ROOT / "dev-tools" / "runtime" / "Shared"
if SHARED_PATH.exists() and str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

try:
    from utils.i18n import load_extra_strings
    load_extra_strings(LEGACY_ROOT / "locales.json")
except Exception:
    pass


def _capture_mode():
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"


def _run_flet(targets):
    from features.video.flet_app import start_app
    start_app(targets)


def main():
    # youtube_downloader is LEGACY_SCOPE='background' – no targets needed
    _run_flet([])


if __name__ == "__main__":
    main()
