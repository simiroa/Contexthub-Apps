"""
Analyze field consistency across all category JSON files.
"""
import json
from pathlib import Path
from collections import defaultdict

cat_dir = Path("config/categories")

# Collect all fields from all files
all_fields = set()
fields_by_file = {}
items_by_file = {}

for json_file in sorted(cat_dir.glob("*.json")):
    data = json.load(open(json_file, encoding='utf-8'))
    items_by_file[json_file.name] = data
    
    if data:
        # Collect all unique fields from all items in this file
        file_fields = set()
        for item in data:
            file_fields.update(item.keys())
        
        fields_by_file[json_file.name] = file_fields
        all_fields.update(file_fields)

print("=" * 60)
print("ALL POSSIBLE FIELDS:")
print("=" * 60)
for field in sorted(all_fields):
    print(f"  - {field}")

print("\n" + "=" * 60)
print("MISSING FIELDS BY FILE:")
print("=" * 60)

for filename in sorted(fields_by_file.keys()):
    missing = sorted(all_fields - fields_by_file[filename])
    if missing:
        print(f"\n{filename}:")
        for field in missing:
            print(f"  ??{field}")
    else:
        print(f"\n{filename}: ??Complete")

print("\n" + "=" * 60)
print("RECOMMENDED STANDARD FIELDS:")
print("=" * 60)
print("""
Required:
  - category
  - id
  - name
  - icon
  - types
  - scope
  - status
  - enabled
  - submenu
  - environment

Optional:
  - show_in_tray
  - dependencies
  - command
""")

