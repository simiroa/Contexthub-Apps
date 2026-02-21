import os
import sys
from pathlib import Path
import runpy

LEGACY_ID = 'pdf_split'
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

# Ensure Shared runtime is in path for i18n
SHARED_PATH = ROOT / "Runtimes" / "Shared"
if SHARED_PATH.exists() and str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

try:
    from utils.i18n import load_extra_strings
    load_extra_strings(LEGACY_ROOT / "locales.json")
except:
    pass


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


def _run_script(script_rel, targets):
    script_path = LEGACY_ROOT / script_rel
    if not script_path.exists():
        raise FileNotFoundError("Missing script: " + str(script_path))
    argv = [str(script_path)] + targets
    old_argv = sys.argv
    try:
        sys.argv = argv
        runpy.run_path(str(script_path), run_name="__main__")
    finally:
        sys.argv = old_argv


def _run_function(targets):
    from features.document.pdf_split_gui import PDFSplitGUI, setup_theme
    setup_theme()
    app = PDFSplitGUI(targets)
    app.mainloop()

def main():
    targets = _pick_targets()
    if LEGACY_SCOPE not in {"background", "tray_only"} and not targets and not _capture_mode():
        return # GUI will handle its own empty targets if needed, but main.py logic is fine
    
    _run_function(targets)


if __name__ == "__main__":
    main()


