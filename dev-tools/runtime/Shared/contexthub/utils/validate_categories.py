import json
from pathlib import Path

cat_dir = Path("config/categories")
issues = []
file_stats = []

for json_file in sorted(cat_dir.glob("*.json")):
    filename = json_file.name
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            issues.append(f"{filename}: Not a list!")
            continue
        
        # Check for issues
        item_count = len(data)
        test_items = [item for item in data if 'test' in item.get('id', '').lower() or 'test' in item.get('name', '').lower()]
        wrong_category = [item for item in data if item.get('category', '').lower() != filename.replace('.json', '').lower() and item.get('category')]
        missing_required = [item for item in data if not item.get('id') or not item.get('name')]
        
        status = "OK"
        if item_count == 0:
            status = "EMPTY"
            issues.append(f"{filename}: Empty file")
        elif test_items:
            status = "TEST DATA"
            issues.append(f"{filename}: Contains {len(test_items)} test items")
        elif wrong_category:
            status = "WRONG CAT"
            issues.append(f"{filename}: {len(wrong_category)} items with wrong category ({[i.get('category') for i in wrong_category[:3]]})")
        elif missing_required:
            status = "INCOMPLETE"
            issues.append(f"{filename}: {len(missing_required)} items missing id/name")
        
        file_stats.append(f"{filename:20} {status:12} {item_count:3} items")
        
    except json.JSONDecodeError as e:
        issues.append(f"{filename}: JSON SYNTAX ERROR - {str(e)[:50]}")
        file_stats.append(f"{filename:20} {'JSON ERROR':12}")
    except Exception as e:
        issues.append(f"{filename}: ERROR - {str(e)[:50]}")
        file_stats.append(f"{filename:20} {'ERROR':12}")

print("FILE STATUS:")
print("=" * 50)
for stat in file_stats:
    print(stat)

print("\n\nISSUES FOUND:")
print("=" * 50)
if issues:
    for issue in issues:
        print(f"??{issue}")
else:
    print("??No issues found!")

print(f"\n\nTotal files: {len(file_stats)}, Issues: {len(issues)}")

