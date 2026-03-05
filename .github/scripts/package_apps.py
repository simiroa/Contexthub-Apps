import os
import json
import zipfile
import shutil

def package_apps():
    apps_dir = "apps"
    dist_dir = "dist"
    market_file = "market.json"
    repo = os.getenv("GITHUB_REPOSITORY", "user/repo")

    if not os.path.exists(apps_dir):
        print(f"Error: {apps_dir} directory not found.")
        return

    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)

    market_data = []

    # Get existing market data if available to preserve items not in current push (optional)
    # For simplicity, we rebuild based on current apps directory

    for root, dirs, files in os.walk(apps_dir):
        if "manifest.json" in files:
            app_id = os.path.basename(root)
            app_path = root
            
            manifest_path = os.path.join(app_path, "manifest.json")
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Packaging
            zip_name = f"{app_id}.zip"
            zip_path = os.path.join(dist_dir, zip_name)

            print(f"Packaging {app_id} v{manifest.get('version', '1.0.0')}...")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for sub_root, sub_dirs, sub_files in os.walk(app_path):
                    for file in sub_files:
                        file_full_path = os.path.join(sub_root, file)
                        arcname = os.path.relpath(file_full_path, app_path)
                        zipf.write(file_full_path, arcname)

            # Registry Entry
            download_url = f"https://github.com/{repo}/releases/download/marketplace-latest/{zip_name}"

            entry = {
                "id": manifest.get("id", app_id),
                "name": manifest.get("name", app_id),
                "description": manifest.get("description", ""),
                "version": manifest.get("version", "1.0.0"),
                "category": manifest.get("runtime", {}).get("category", "uncategorized"),
                "icon_url": manifest.get("icon_url", ""),
                "zip_url": download_url
            }
            market_data.append(entry)

    # Save market.json to root
    with open(market_file, 'w', encoding='utf-8') as f:
        json.dump(market_data, f, indent=4, ensure_ascii=False)

    print(f"Successfully updated {market_file} with {len(market_data)} apps.")

if __name__ == "__main__":
    package_apps()
