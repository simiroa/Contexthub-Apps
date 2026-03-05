import os
import sys
import subprocess
import time
from pathlib import Path

def dry_run_app(app_name, main_path, env_path):
    print(f"\n--- Dry-running: {app_name} ---")
    
    # Set environment variables
    env = os.environ.copy()
    env["CTX_HEADLESS"] = "1"
    env["CTX_CAPTURE_MODE"] = "1"
    env["CTX_APP_ROOT"] = str(Path(main_path).parent)
    
    python_exe = str(Path(env_path) / "Scripts" / "python.exe")
    
    try:
        # Run in headless mode which should trigger the GUI but close quickly (as seen in convert_gui.py)
        # or just exit if logic handles it.
        # We use a short timeout as a safety measure.
        result = subprocess.run(
            [python_exe, main_path, "--dev"], 
            env=env, 
            timeout=15,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print("Stderr:", result.stderr)
        return True
    except subprocess.TimeoutExpired:
        print(f"Warning: {app_name} dry-run timed out.")
        return False
    except Exception as e:
        print(f"Error dry-running {app_name}: {e}")
        return False

def main():
    root = Path(r"c:\Users\HG_maison\Documents\Contexthub")
    apps_root = root / "Apps_installed" / "document"
    # Document apps usually use the same env as 3D or a specific one?
    # Based on shared_root check in Apps_installed/document/_engine/utils/__init__.py
    # They seem to rely on the general environment. Use Runtimes/Envs/3d as it's common.
    env_path = root / "Runtimes" / "Envs" / "3d"
    
    apps = [
        ("doc_convert", apps_root / "doc_convert" / "main.py"),
        ("pdf_merge", apps_root / "pdf_merge" / "main.py"),
        ("pdf_split", apps_root / "pdf_split" / "main.py")
    ]
    
    for name, path in apps:
        dry_run_app(name, str(path), str(env_path))

if __name__ == "__main__":
    main()
