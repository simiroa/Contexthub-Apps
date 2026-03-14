import os
import sys
from pathlib import Path
import runpy

LEGACY_ID = 'resize_power_of_2'
LEGACY_SCOPE = 'file'
USE_MENU = False
SCRIPT_REL = "features/image/resize_gui.py"

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"
SHARED_ROOT = ROOT / "dev-tools" / "runtime" / "Shared"
SHARED_PACKAGE_ROOT = SHARED_ROOT / "contexthub"
os.chdir(LEGACY_ROOT)
for path in (LEGACY_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)
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

    args = [a for a in sys.argv[1:] if a]
    if args:
        return args

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()

        if LEGACY_SCOPE in {"items"}:
            paths = filedialog.askopenfilenames(title=LEGACY_ID)
            return list(paths)
        if LEGACY_SCOPE in {"directory"}:
            path = filedialog.askdirectory(title=LEGACY_ID)
            return [path] if path else []
        path = filedialog.askopenfilename(title=LEGACY_ID)
        return [path] if path else []
    except Exception:
        return []


def _run_flet(targets):
    try:
        from features.image.resize_power_of_2.flet_app import start_app
        start_app(targets)
    except ImportError as e:
        print(f"Failed to load Flet app: {e}")
        raise e


def main():
    targets = _pick_targets()
    if LEGACY_SCOPE not in {"background", "tray_only", "standalone"} and not targets and not _capture_mode():
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("ContextHub", "No target selected.")
        except Exception:
            pass
        return

    _run_flet(targets)


if __name__ == "__main__":
    main()
