import os
import sys
from pathlib import Path

LEGACY_ID = 'doc_convert'
LEGACY_SCOPE = 'file'

ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"
os.chdir(LEGACY_ROOT)
sys.path.insert(0, str(LEGACY_ROOT))
if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

# Ensure Shared runtime is in path for i18n and Flet tokens
SHARED_PATH = ROOT / "Runtimes" / "Shared"
if SHARED_PATH.exists() and str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

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

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()

        path = filedialog.askopenfilename(title=LEGACY_ID)
        return [path] if path else []
    except Exception:
        return []


def _run_flet(targets):
    from features.document.doc_convert.flet_app import start_app
    start_app(targets)


def main():
    # Load locales
    targets = _pick_targets()
    if LEGACY_SCOPE not in {"background", "tray_only", "standalone"} and not targets and not _capture_mode():
        return

    _run_flet(targets)


if __name__ == "__main__":
    main()
