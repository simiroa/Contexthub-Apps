"""
Standardize all category JSON files with consistent fields.
Supports both list-based and dictionary-based (nested features) configurations.
"""
import json
import os
from pathlib import Path

# Fix path relative to script location for robustness
BASE_DIR = Path(__file__).parent.parent.parent
cat_dir = BASE_DIR / "config" / "categories"

# Standard defaults for missing required fields
DEFAULTS = {
    "enabled": True,
    "submenu": "ContextUp",
    "environment": "system",
    "show_in_tray": False,
    "dependencies": [],
    "external_tools": [],
}

# Required fields (must be present)
REQUIRED_FIELDS = [
    "category", "id", "name", "icon", "types", "scope", 
    "status", "enabled", "submenu", "environment", "show_in_tray",
    "dependencies", "external_tools"
]

# Field order for consistent formatting
FIELD_ORDER = [
    "category", "id", "name", "icon", "types", "scope", "status",
    "enabled", "submenu", "show_in_tray", "environment", 
    "dependencies", "external_tools", "command", "hotkey"
]

def standardize_item(item, category_name):
    """Standardize a single item/feature object."""
    changes = []
    
    # Ensure category field matches filename if not present
    if "category" not in item:
        item["category"] = category_name
        changes.append("category")
    
    # Add missing required fields from defaults
    for field in REQUIRED_FIELDS:
        if field not in item:
            if field in DEFAULTS:
                item[field] = DEFAULTS[field]
                changes.append(f"+{field}")
            else:
                # Critical fields missing but no default
                if field in ["id", "name"]:
                    print(f"  [ERROR] Critical field missing: {field}")
    
    # Reorder fields for consistency
    ordered_item = {}
    for field in FIELD_ORDER:
        if field in item:
            ordered_item[field] = item[field]
    
    # Add any remaining fields not in FIELD_ORDER
    for key, value in item.items():
        if key not in ordered_item:
            ordered_item[key] = value
    
    item.clear()
    item.update(ordered_item)
    return changes

def process_file(json_file):
    print(f"\nProcessing {json_file.name}...")
    category_name = json_file.stem.capitalize()
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [ERROR] Failed to load: {e}")
        return False

    if not data:
        print("  Skipping empty file")
        return False
    
    file_modified = False
    
    if isinstance(data, list):
        # List of items
        for item in data:
            changes = standardize_item(item, category_name)
            if changes:
                file_modified = True
                print(f"  - {item.get('id', '???')}: {', '.join(changes)}")
    
    elif isinstance(data, dict):
        # Dictionary structure (e.g. ComfyUI)
        # Root can also be an item if it has an ID
        if "id" in data:
            changes = standardize_item(data, category_name)
            if changes:
                file_modified = True
        
        # Check for nested features
        features = data.get("features")
        if isinstance(features, list):
            for item in features:
                changes = standardize_item(item, category_name)
                if changes:
                    file_modified = True
                    print(f"  - {item.get('id', '???')} (nested): {', '.join(changes)}")
    
    if file_modified:
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"  [SUCCESS] Standardized and saved.")
        except Exception as e:
            print(f"  [ERROR] Failed to save: {e}")
    else:
        print("  Already standardized.")
    
    return file_modified

def main():
    if not cat_dir.exists():
        print(f"[ERROR] Category directory not found: {cat_dir}")
        return

    files = sorted(cat_dir.glob("*.json"))
    modified_count = 0
    
    for json_file in files:
        if process_file(json_file):
            modified_count += 1
            
    print(f"\nStandardization complete. Modified {modified_count}/{len(files)} files.")

if __name__ == "__main__":
    main()


