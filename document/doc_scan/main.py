import os
import sys
from pathlib import Path

LEGACY_ID = 'doc_scan'
LEGACY_SCOPE = 'file'
ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"
os.chdir(LEGACY_ROOT)
sys.path.insert(0, str(LEGACY_ROOT))
if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)
SHARED_ROOT = ROOT / "dev-tools" / "runtime" / "Shared"
if SHARED_ROOT.exists() and str(SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(SHARED_ROOT))

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

        paths = filedialog.askopenfilenames(title=LEGACY_ID, filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.webp")])
        return list(paths)
    except Exception:
        return []

def _run_flet(targets):
    from features.document.doc_scan_flet_app import start_app
    start_app(targets)

def main():
    try:
        from utils.i18n import load_extra_strings
        loc_file = LEGACY_ROOT / "locales.json"
        if loc_file.exists():
            load_extra_strings(loc_file)
    except Exception: pass

    targets = _pick_targets()
    if not targets and not _capture_mode():
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
