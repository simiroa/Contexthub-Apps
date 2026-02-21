import os
import sys
from pathlib import Path
import runpy

LEGACY_ID = 'esrgan_upscale'
LEGACY_SCOPE = 'file'
USE_MENU = False
SCRIPT_REL = None

ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"
os.chdir(LEGACY_ROOT)
sys.path.insert(0, str(LEGACY_ROOT))
if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)


def _capture_mode():
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"

def _pick_targets():
    if LEGACY_SCOPE in {"background", "tray_only"}:
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


def _run_function(targets):
    # Refactored to use the new GUI application
    from features.ai.standalone.upscale_app import UpscaleGUI
    target = targets[0] if targets else None
    try:
        app = UpscaleGUI(target)
        app.mainloop()
    except Exception as e:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("ContextHub Error", f"Failed to launch Upscale GUI: {e}")


def main():
    targets = _pick_targets()
    if LEGACY_SCOPE not in {"background", "tray_only"} and not targets and not _capture_mode():
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("ContextHub", "No target selected.")
        except Exception:
            pass
        return

    _run_function(targets)


if __name__ == "__main__":
    main()
