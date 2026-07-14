import os
import json
import zipfile
import argparse
import sys

def package_apps(sync_registry_only=False, check_only=False):
    dist_dir = "dist"
    market_file = "market.json"
    repo = os.getenv("GITHUB_REPOSITORY", "simiroa/Contexthub-Apps")
    base_url = f"https://raw.githubusercontent.com/{repo}/main"
    release_url = f"https://github.com/{repo}/releases/download/marketplace-assets"

    # Categories are top-level folders except for these:
    exclude_dirs = {".git", ".github", "dist", "tmp", "venv", ".gemini", "node_modules"}
    
    if not sync_registry_only and not check_only:
        if not os.path.exists(dist_dir):
            os.makedirs(dist_dir)

    market_data = []
    
    # Iterate through each directory in current root
    for entry_name in os.listdir("."):
        if not os.path.isdir(entry_name) or entry_name in exclude_dirs:
            continue
            
        category = entry_name
        category_path = os.path.join(".", category)
        
        # Look for app folders inside the category
        for app_folder in os.listdir(category_path):
            app_path = os.path.join(category_path, app_folder)
            if not os.path.isdir(app_path):
                continue
                
            manifest_path = os.path.join(app_path, "manifest.json")
            if not os.path.exists(manifest_path):
                continue

            # Accept UTF-8 manifests with or without BOM to avoid CI failures
            # caused by editor-dependent JSON encoding.
            with open(manifest_path, 'r', encoding='utf-8-sig') as f:
                manifest = json.load(f)

            # Tombstones from native SystemC parity removals (folders deleted in same PR when possible)
            if manifest.get("removed") is True:
                print(f"Skipping removed app: {category}/{app_folder}")
                continue

            app_id = manifest.get("id", app_folder)
            version = manifest.get("version", "1.0.0")

            # 1. Validation: manual.md is required
            manual_path = os.path.join(app_path, "manual.md")
            if not os.path.exists(manual_path):
                print(f"Error: Missing manual.md in {app_path}")
                exit(1)

            # 2. Icon URL logic (png preferred over ico)
            icon_name = "icon.png"
            if not os.path.exists(os.path.join(app_path, icon_name)):
                if os.path.exists(os.path.join(app_path, "icon.ico")):
                    icon_name = "icon.ico"
                else:
                    print(f"Warning: No icon found in {app_path}")
            
            icon_url = f"{base_url}/{category}/{app_folder}/{icon_name}"

            # 3. Packaging
            zip_name = f"{app_id}.zip"
            zip_path = os.path.join(dist_dir, zip_name)

            if not sync_registry_only and not check_only:
                print(f"Packaging {app_id} v{version}...")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for sub_root, sub_dirs, sub_files in os.walk(app_path):
                        for file in sub_files:
                            file_full_path = os.path.join(sub_root, file)
                            arcname = os.path.relpath(file_full_path, app_path)
                            zipf.write(file_full_path, arcname)

            # 4. Registry Entry
            entry = {
                "id": app_id,
                "name": manifest.get("name", app_id),
                "description": manifest.get("description", ""),
                "version": version,
                "category": category,
                "icon_url": icon_url,
                "zip_url": f"{release_url}/{zip_name}"
            }
            market_data.append(entry)

    # Save or Check market.json to root
    if check_only:
        if not os.path.exists(market_file):
            print(f"Error: {market_file} does not exist.")
            sys.exit(1)
        with open(market_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        if existing_data != market_data:
            print(f"Error: {market_file} is out of sync with actual apps.")
            print("Please run 'python .github/scripts/package_apps.py --sync-registry-only' and commit the changes.")
            sys.exit(1)
        print(f"Success: {market_file} is perfectly in sync.")
    else:
        with open(market_file, 'w', encoding='utf-8') as f:
            json.dump(market_data, f, indent=4, ensure_ascii=False)
            # Add a trailing newline to prevent diff warnings
            f.write('\n')
        print(f"Successfully updated {market_file} with {len(market_data)} apps.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Apps and/or Sync Market Registry")
    parser.add_argument("--sync-registry-only", action="store_true", help="Only update market.json without packaging ZIPs")
    parser.add_argument("--check-only", action="store_true", help="Fail if market.json is out of sync (used for CI PR checks)")
    args = parser.parse_args()
    
    package_apps(sync_registry_only=args.sync_registry_only, check_only=args.check_only)
