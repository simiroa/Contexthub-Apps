"""
Utility to run AI scripts using the embedded Python environment.
Includes process lifecycle management.
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path

def _load_settings():
    try:
        from contexthub.core.settings import load_settings
        return load_settings()
    except Exception:
        return {}


def _find_conda_exe(settings):
    candidates = [
        settings.get("AI_CONDA_EXE"),
        os.environ.get("CTX_AI_CONDA_EXE"),
        os.environ.get("CONDA_EXE"),
        shutil.which("conda"),
        shutil.which("conda.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def _resolve_conda_python(settings):
    env_path = settings.get("AI_CONDA_ENV_PATH") or os.environ.get("CTX_AI_CONDA_ENV_PATH")
    if env_path:
        candidate = Path(env_path) / "python.exe"
        if candidate.exists():
            return candidate
        return None

    conda_exe = _find_conda_exe(settings)
    if not conda_exe:
        return None

    env_name = settings.get("AI_CONDA_ENV_NAME") or os.environ.get("CTX_AI_CONDA_ENV_NAME") or "contexthub-ai"
    try:
        result = subprocess.run(
            [str(conda_exe), "info", "--base"],
            capture_output=True,
            text=True,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        base_path = Path((result.stdout or "").strip())
        candidate = base_path / "envs" / env_name / "python.exe"
        if candidate.exists():
            return candidate
    except Exception:
        return None

    return None


def _find_python():
    """
    Prefer:
    1. Configured Conda AI env
    2. Dedicated AI Env: Runtimes/Envs/ai/Scripts/python.exe
    3. Embedded python: tools/python/python.exe
    4. Custom path from settings
    5. Current interpreter
    """
    project_root = Path(__file__).resolve().parents[4]
    settings = _load_settings()

    if settings.get("AI_ENV_MODE", "prefer_conda") != "disabled":
        conda_python = _resolve_conda_python(settings)
        if conda_python:
            return conda_python
    
    # 2. AI categorical environment (New Standard)
    ai_env = project_root / "Runtimes" / "Envs" / "ai" / "Scripts" / "python.exe"
    if ai_env.exists():
        return ai_env

    # 3. General embedded environment
    embedded = project_root / "tools" / "python" / "python.exe"
    if embedded.exists():
        return embedded

    custom = settings.get("PYTHON_PATH")
    if custom and Path(custom).exists():
        return Path(custom)

    return Path(sys.executable)

def start_ai_script(script_name, *args, **kwargs):
    """
    Start AI script and return the subprocess.Popen object for tracking.
    """
    python_exe = _find_python()
    root = Path(__file__).resolve().parents[1]
    requested_path = Path(script_name)
    if requested_path.is_absolute() and requested_path.exists():
        script_path = requested_path
    else:
        script_path = None
        candidates = [
            root / "features" / "ai" / "standalone" / script_name,
            root / "scripts" / "ai_standalone" / script_name
        ]
        
        for p in candidates:
            if p.exists():
                script_path = p
                break
            
    if not script_path:
        raise FileNotFoundError(f"AI script not found: {script_name}")
    
    cmd = [str(python_exe), str(script_path)] + list(args)
    
    # We use creationflags to hide console on Windows
    creationflags = 0x08000000 if sys.platform == "win32" else 0
    
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        creationflags=creationflags,
        cwd=str(root.parent)
    )

def kill_process_tree(process):
    """Safely kill a process and its children."""
    if not process or process.poll() is not None:
        return
    
    try:
        if sys.platform == "win32":
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                           capture_output=True, creationflags=0x08000000)
        else:
            process.terminate()
            try:
                process.wait(timeout=2)
            except:
                process.kill()
    except Exception as e:
        print(f"Error killing process {process.pid}: {e}")

def run_ai_script(script_name, *args, **kwargs):
    """
    Synchronous wrapper for backward compatibility.
    """
    try:
        p = start_ai_script(script_name, *args, **kwargs)
        stdout, _ = p.communicate()
        return (p.returncode == 0), stdout
    except Exception as e:
        return False, str(e)

import json

def run_ai_script_streaming(script_name, *args, **kwargs):
    """
    Generator that yields output lines from the AI script in real-time.
    If a line is valid JSON, it yields it as a dict.
    Yields: (is_error, line_or_dict)
    """
    try:
        process = start_ai_script(script_name, *args, **kwargs)
        
        for line in process.stdout:
            clean_line = line.strip()
            if not clean_line: continue
            
            # Try parsing as JSON
            if clean_line.startswith('{') and clean_line.endswith('}'):
                try:
                    data = json.loads(clean_line)
                    yield False, data
                    continue
                except:
                    pass
                    
            yield False, clean_line
            
        process.wait()
        
        if process.returncode != 0:
            yield True, {"status": "error", "code": process.returncode, "message": f"Process exited with code {process.returncode}"}
            
    except Exception as e:
        yield True, {"status": "error", "message": str(e)}
