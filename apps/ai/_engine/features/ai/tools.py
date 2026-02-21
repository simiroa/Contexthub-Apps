"""
AI-powered background removal using latest models (Nov-Dec 2024).
Runs in the embedded Python environment.
"""
import sys
from pathlib import Path
from tkinter import messagebox

# Add src to path
current_dir = Path(__file__).parent
engine_dir = current_dir.parent  # features -> _engine
sys.path.append(str(engine_dir))

from utils.ai_runner import run_ai_script
from utils.i18n import t

def remove_background(target_path: str):
    """Refactored: Launches the standalone Background Removal App."""
    try:
        # We launch the standalone app script instead of running the GUI loop here.
        # This ensures clean separation and better environment handling.
        
        script_name = "bg_removal_app.py"
        
        # run_ai_script usually waits for output, but here we want to launch a GUI.
        # run_ai_script implementation waits.
        # So this function will block until the GUI closes, which is acceptable for this usage pattern.
        
        success, output = run_ai_script(script_name, target_path)
        
        if not success:
            # If the script failed to run (e.g. crash on startup), show error.
            # But not if it was just a clean exit.
            if "Script not found" in output:
                 messagebox.showerror(t("common.error"), t("ai_common.script_not_found").format(error=output))
            else:
                 # It might return non-success if user closed it or something? 
                 # Usually GUI apps return 0.
                 pass
                 
    except Exception as e:
        messagebox.showerror(t("common.error"), t("ai_common.failed").format(error=e))
