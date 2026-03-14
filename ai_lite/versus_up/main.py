import os
import sys
from pathlib import Path
import runpy

LEGACY_ID = 'versus_up'
LEGACY_SCOPE = 'standalone'
USE_MENU = False
SCRIPT_REL = "features/versus_up/versus_up_flet_app.py"

# Local PATH setup
APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"

os.chdir(LEGACY_ROOT)
if str(LEGACY_ROOT) not in sys.path:
    sys.path.insert(0, str(LEGACY_ROOT))

# Add feature directory to sys.path for internal imports
feature_dir = LEGACY_ROOT / "features" / "versus_up"
if str(feature_dir) not in sys.path:
    sys.path.insert(0, str(feature_dir))

# ContextHub environment variable
if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

def main():
    script_path = LEGACY_ROOT / SCRIPT_REL
    if not script_path.exists():
        print(f"Error: Missing script at {script_path}")
        return
        
    # Set targets (empty for standalone)
    targets = []
    
    # Prepare sys.argv
    argv = [str(script_path)] + targets
    old_argv = sys.argv
    try:
        sys.argv = argv
        runpy.run_path(str(script_path), run_name="__main__")
    finally:
        sys.argv = old_argv

if __name__ == "__main__":
    main()
