import json
import os
from pathlib import Path

from .paths import SETTINGS_FILE, SECRETS_FILE

DEFAULT_SETTINGS = {
    "GEMINI_API_KEY": "",
    "GEMINI_MODEL": "gemini-2.5-flash-lite",
    "OLLAMA_URL": "http://localhost:11434",
    "PYTHON_PATH": "",
    "AI_ENV_MODE": "prefer_conda",
    "AI_CONDA_EXE": "",
    "AI_CONDA_ENV_NAME": "contexthub-ai",
    "AI_CONDA_ENV_PATH": "",
    "THEME": "dark",
    "FFMPEG_PATH": "",
    "BLENDER_PATH": "",
    "MAYO_PATH": "",
    "COMFYUI_PATH": "",
    "COMFYUI_GPU_OPTIONS": {
        "windows_standalone": True,
        "sage_attention": False,
        "fp16_fast_accumulation": False,
        "low_vram": False,
        "cpu_only": False,
        "vram_auto_unload_minutes": 0  # 0 = disabled, >0 = auto unload after N minutes idle
    },
    "CATEGORY_COLORS": {
        "Image": "#2ecc71",
        "Video": "#3498db",
        "Audio": "#e67e22",
        "3D": "#9b59b6",
        "Sys": "#95a5a6",
        "Document": "#f1c40f",
        "Custom": "#ecf0f1"
    },
    "BACKUP_EXCLUDE": [],
    "TRAY_ENABLED": False,
    "CHECK_UPDATES_ON_STARTUP": True,
    "MENU_POSITION_TOP": True,
    "WIN11_MAIN_MENU_ENABLED": False
}

SENSITIVE_KEYS = ["GEMINI_API_KEY"]

def load_settings():
    """Load settings from JSON and set environment variables."""
    settings = DEFAULT_SETTINGS.copy()
    
    # Load main settings
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8-sig', errors='replace') as f:
                data = json.load(f)
                settings.update(data)
        except Exception as e:
            print(f"Error loading settings: {e}")
            
    # Load secrets (overrides main settings if present)
    if SECRETS_FILE.exists():
        try:
            with open(SECRETS_FILE, 'r', encoding='utf-8-sig', errors='replace') as f:
                secrets = json.load(f)
                for key in SENSITIVE_KEYS:
                    if key in secrets:
                        settings[key] = secrets[key]
        except Exception as e:
            print(f"Error loading secrets: {e}")
            
    # Set environment variables
    if settings.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = settings["GEMINI_API_KEY"]
        
    if settings.get("OLLAMA_URL"):
        os.environ["OLLAMA_HOST"] = settings["OLLAMA_URL"]

    # Auto-detect bundled Python if not configured
    if not settings.get("PYTHON_PATH"):
        project_root = SETTINGS_FILE.parent.parent
        bundled_python = project_root / "tools" / "python" / "python.exe"
        if bundled_python.exists():
            settings["PYTHON_PATH"] = str(bundled_python)
        else:
            import sys
            settings["PYTHON_PATH"] = sys.executable

    return settings

def save_settings(new_settings):
    """Save settings to JSON, separating secrets."""
    try:
        # Prepare content for settings.json (exclude secrets)
        settings_to_save = new_settings.copy()
        secrets_to_save = {}
        
        for key in SENSITIVE_KEYS:
            if key in settings_to_save:
                secrets_to_save[key] = settings_to_save.pop(key)
                
        # Save main settings
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8-sig') as f:
            json.dump(settings_to_save, f, indent=4, ensure_ascii=False)
            
        # Save secrets if there are any to update
        if secrets_to_save:
            existing_secrets = {}
            if SECRETS_FILE.exists():
                try:
                    with open(SECRETS_FILE, 'r') as f:
                        existing_secrets = json.load(f)
                except:
                    pass
            
            existing_secrets.update(secrets_to_save)
            
            with open(SECRETS_FILE, 'w', encoding='utf-8-sig') as f:
                json.dump(existing_secrets, f, indent=4, ensure_ascii=False)
                
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False
