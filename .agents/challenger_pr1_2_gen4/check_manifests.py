import json
import pathlib

root = pathlib.Path(r"C:\Users\HG_maison\Documents\Contexthub-Apps")
manifests = sorted(root.rglob("manifest.json"))

print("Found manifests:")
for m in manifests:
    if "agent-docs/templates" in m.as_posix().replace("\\", "/"):
        continue
    try:
        data = json.loads(m.read_text(encoding="utf-8-sig"))
        app_id = data.get("id")
        ui = data.get("ui", {})
        template = ui.get("template")
        category = m.parent.parent.name
        print(f"App: {app_id} | Category: {category} | Template: {template} | Path: {m.relative_to(root)}")
    except Exception as e:
        print(f"Error reading {m}: {e}")
