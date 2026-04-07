import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ManifestEntry:
    app_id: str
    name: str
    category: str
    app_dir: Path
    entry_point: str
    mode: str
    context_enabled: bool
    context_extensions: List[str]


def _load_manifest(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None


def _normalize_extensions(exts: Iterable[str]) -> List[str]:
    normalized = []
    for ext in exts:
        if not ext:
            continue
        normalized.append(str(ext).strip().lower())
    return normalized


def scan_manifests(root_dir: Path) -> Dict[str, ManifestEntry]:
    apps_root = root_dir / "Apps_installed"
    manifests = {}
    for path in apps_root.rglob("manifest.json"):
        data = _load_manifest(path)
        if not data:
            continue
        app_id = data.get("id") or path.parent.name
        name = data.get("name") or app_id
        runtime = data.get("runtime") or {}
        category = runtime.get("category") or path.parent.parent.name
        execution = data.get("execution") or {}
        entry_point = execution.get("entry_point") or "main.py"
        mode = execution.get("mode") or "gui"
        triggers = data.get("triggers") or {}
        context_menu = triggers.get("context_menu") or {}
        context_enabled = bool(context_menu.get("enabled", False))
        context_extensions = _normalize_extensions(context_menu.get("extensions") or [])

        manifests[app_id] = ManifestEntry(
            app_id=app_id,
            name=name,
            category=category,
            app_dir=path.parent,
            entry_point=entry_point,
            mode=mode,
            context_enabled=context_enabled,
            context_extensions=context_extensions,
        )

    return manifests
