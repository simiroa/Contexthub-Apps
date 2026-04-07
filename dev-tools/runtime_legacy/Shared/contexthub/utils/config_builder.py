import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MENU_CATEGORIES_DIR = PROJECT_ROOT / "config" / "menu" / "categories"
OUTPUT_CONFIG_PATH = PROJECT_ROOT / "config" / "menu_config.json"

def build_config():
    if not MENU_CATEGORIES_DIR.exists():
        print(f"Menu categories directory not found: {MENU_CATEGORIES_DIR}")
        return

    combined_config = []
    
    # List all json files
    files = [f for f in os.listdir(MENU_CATEGORIES_DIR) if f.endswith('.json')]
    
    print(f"Found {len(files)} category files.")
    
    for filename in files:
        file_path = MENU_CATEGORIES_DIR / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    combined_config.extend(data)
                elif isinstance(data, dict):
                    combined_config.append(data)
                else:
                    print(f"Warning: {filename} contains invalid data type (not list or dict).")
        except Exception as e:
            print(f"Error loading {filename}: {e}")

    # Sort by Category then Name for tidiness
    combined_config.sort(key=lambda x: (x.get('category', 'ZZZ'), x.get('name', '')))

    # Write to menu_config.json
    with open(OUTPUT_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(combined_config, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully rebuilt menu_config.json with {len(combined_config)} entries.")

if __name__ == "__main__":
    build_config()
