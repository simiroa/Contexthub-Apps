import os
import sys
from pathlib import Path
import runpy

LEGACY_ID = 'ai_text_lab'
LEGACY_SCOPE = 'standalone'
USE_MENU = False
SCRIPT_REL = 'features/tools/ai_text_lab_flet_app.py'

ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"

os.chdir(LEGACY_ROOT)
if str(LEGACY_ROOT) not in sys.path:
    sys.path.insert(0, str(LEGACY_ROOT))

# Add feature directory to sys.path for internal imports
feature_dir = LEGACY_ROOT / "features" / "tools"
if str(feature_dir) not in sys.path:
    sys.path.insert(0, str(feature_dir))

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

def main():
    targets = _pick_targets()
    if LEGACY_SCOPE not in {"background", "tray_only", "standalone"} and not targets and not _capture_mode():
        return

    _run_script(SCRIPT_REL, targets)

if __name__ == "__main__":
    main()
