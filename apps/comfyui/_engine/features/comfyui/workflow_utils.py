
import json
import random
from pathlib import Path

def load_workflow(workflow_path):
    """Loads a workflow JSON file."""
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading workflow {workflow_path}: {e}")
        return None

def update_node_value(workflow, node_id, input_key, value):
    """Updates a specific value in the workflow dictionary."""
    if str(node_id) in workflow:
        if "inputs" in workflow[str(node_id)]:
            workflow[str(node_id)]["inputs"][input_key] = value
            return True
    return False

def find_node_by_class(workflow, class_type):
    """Finds first node ID with matching class type."""
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == class_type:
            return node_id
    return None

def set_seed(workflow, seed=None):
    """Sets a random seed for all KSampler or Seed-based nodes."""
    if seed is None:
        seed = random.randint(1, 1000000000)
    
    count = 0
    for node_id, node_data in workflow.items():
        if "inputs" in node_data:
            if "seed" in node_data["inputs"]:
                node_data["inputs"]["seed"] = seed
                count += 1
            if "noise_seed" in node_data["inputs"]:
                node_data["inputs"]["noise_seed"] = seed
                count += 1
    return count

# --- Centralized Workflow Registry ---

WORKFLOW_MAP = {
    "z_image_turbo": "ContextUp/assets/workflows/z_image/turbo.json",
    "ace_audio_edit": "ContextUp/assets/workflows/audio/ace_step_1_m2m_editing.json",
    "ace_audio_song": "ContextUp/assets/workflows/audio/ace_step_1_t2a_song.json",
    "ace_audio_instrumental": "ContextUp/assets/workflows/audio/ace_step_1_t2a_instrumentals.json",
    "seedvr2_upscale": "ContextUp/assets/workflows/seedvr2/upscale.json"
}

def get_workflow_path(key):
    """
    Returns the absolute path for a registered workflow key.
    key: string key from WORKFLOW_MAP
    """
    if key not in WORKFLOW_MAP:
        print(f"⚠️ Workflow key '{key}' not found in registry.")
        return None
        
    # Resolve relative to ContextUp root
    # This utils file is in src/features/comfyui/
    # Root is ../../../
    root = Path(__file__).resolve().parents[3] 
    
    # WORKFLOW_MAP paths start with "ContextUp/..." 
    # Current structure assumes ContextUp root contains 'src', 'assets' etc.
    # If WORKFLOW_MAP implies "ContextUp" as the repo root:
    # We should strip "ContextUp/" if our root is already inside it? 
    # Or matches provided path structure.
    
    rel_path = WORKFLOW_MAP[key]
    # Handle potentially double "ContextUp" if dev environment differs
    # Ideally, mapped paths should be relative to Project Root.
    
    if rel_path.startswith("ContextUp/"):
        rel_path = rel_path.replace("ContextUp/", "", 1)
        
    full_path = root / rel_path
    
    if not full_path.exists():
         # Try looking in 'assets' directly if path logic is skewed
         alt_path = root / "assets" / "workflows" / Path(rel_path).name
         if alt_path.exists():
             return alt_path
             
         print(f"❌ Workflow file missing at: {full_path}")
         return None
         
    return full_path
