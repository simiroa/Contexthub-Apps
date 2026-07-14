import os
import json

exclude_dirs = {".git", ".github", "dist", "tmp", "venv", ".gemini", "node_modules", "agent-docs"}

apps = []
for entry_name in os.listdir("."):
    if not os.path.isdir(entry_name) or entry_name in exclude_dirs:
        continue
        
    category = entry_name
    category_path = os.path.join(".", category)
    
    for app_folder in os.listdir(category_path):
        app_path = os.path.join(category_path, app_folder)
        if not os.path.isdir(app_path):
            continue
            
        manifest_path = os.path.join(app_path, "manifest.json")
        if not os.path.exists(manifest_path):
            continue

        with open(manifest_path, 'r', encoding='utf-8-sig') as f:
            manifest = json.load(f)

        apps.append({
            "path": app_path,
            "id": manifest.get("id"),
            "removed": manifest.get("removed", False)
        })

print(f"Total apps found: {len(apps)}")
for app in apps:
    print(f"Path: {app['path']}, ID: {app['id']}, Removed: {app['removed']}")
