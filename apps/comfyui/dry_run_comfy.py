import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Using the dedicated comfyui runtime
PYTHON_EXE = ROOT / "Runtimes" / "Envs" / "comfyui" / "Scripts" / "python.exe"
COMFY_APPS_DIR = ROOT / "Apps_installed" / "comfyui"

def run_dry(app_id):
    print(f"\n--- Dry-running: {app_id} ---")
    app_path = COMFY_APPS_DIR / app_id / "main.py"
    if not app_path.exists():
        print(f"Error: {app_path} not found.")
        return

    env = os.environ.copy()
    env["CTX_HEADLESS"] = "1"
    env["CTX_CAPTURE_MODE"] = "1"
    env["CTX_APP_ROOT"] = str(COMFY_APPS_DIR / app_id)
    env["CTX_SHARED_ROOT"] = str(ROOT / "Runtimes" / "Shared" / "contexthub")
    
    # ComfyUI engine needs to be in path
    env["PYTHONPATH"] = f"{ROOT / 'Runtimes' / 'Shared'};{COMFY_APPS_DIR / '_engine'}"

    cmd = [str(PYTHON_EXE), str(app_path)]
    
    try:
        process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            time.sleep(10)
            process.terminate()
            stdout, _ = process.communicate()
            print(f"  [STDOUT] {stdout}")
        except Exception as e:
            process.kill()
            print(f"  [EXEC ERROR] {e}")
            
    except Exception as e:
        print(f"Failed to run {app_id}: {e}")

if __name__ == "__main__":
    for app in ["creative_studio_z", "ace_audio_editor", "creative_studio_advanced", "seedvr2_upscaler", "comfyui_dashboard"]:
        run_dry(app)
