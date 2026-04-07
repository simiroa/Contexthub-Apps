import json
from pathlib import Path
import os
import threading

# Global lock for file access
_lock = threading.Lock()

def _get_config_path():
    """Get path to gui_states.json"""
    # Assuming this file is in src/utils/
    # Userdata is in ../../userdata/
    root = Path(__file__).parent.parent.parent
    userdata_dir = root / "userdata"
    userdata_dir.mkdir(exist_ok=True)
    return userdata_dir / "gui_states.json"

def load_gui_state(tool_id, defaults=None):
    """
    Load state for a specific tool.
    
    Args:
        tool_id (str): Unique identifier for the tool (e.g. 'pdf_ocr')
        defaults (dict): Default values if not found.
    
    Returns:
        dict: The state dictionary.
    """
    if defaults is None:
        defaults = {}
        
    path = _get_config_path()
    if not path.exists():
        return defaults

    try:
        with _lock:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(tool_id, defaults)
    except Exception as e:
        print(f"Error loading GUI state: {e}")
        return defaults

def save_gui_state(tool_id, state):
    """
    Save state for a specific tool.
    
    Args:
        tool_id (str): Unique identifier for the tool.
        state (dict): Dictionary of values to save.
    """
    path = _get_config_path()
    
    with _lock:
        data = {}
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                pass # Corrupt or empty
        
        # Merge/Overwrite
        current = data.get(tool_id, {})
        if isinstance(current, dict) and isinstance(state, dict):
            current.update(state)
            data[tool_id] = current
        else:
            data[tool_id] = state
            
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving GUI state: {e}")
