from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from features.versus_up.versus_up_state import CriterionRecord, ProductRecord, ProjectMeta, VisionCache


class VersusUpProjectStore:
    def load_recent_projects(self, recent_file: Path) -> list[str]:
        if not recent_file.exists():
            return []
        try:
            data = json.loads(recent_file.read_text(encoding="utf-8"))
            return [str(item) for item in data.get("recent_projects", []) if str(item)]
        except Exception:
            return []

    def save_recent_projects(self, recent_file: Path, recent_projects: list[str]) -> list[str]:
        unique: list[str] = []
        for path in recent_projects:
            if path not in unique:
                unique.append(path)
        recent_projects = unique[:12]
        recent_file.write_text(json.dumps({"recent_projects": recent_projects}, indent=2, ensure_ascii=False), encoding="utf-8")
        return recent_projects

    def apply_project_payload(self, state, payload: dict[str, Any], project_path: Path | None = None) -> None:
        state.schema_version = str(payload.get("schema_version", "2.0"))
        state.project_meta = ProjectMeta.from_dict(dict(payload.get("project", {}) or {}))
        state.products = [ProductRecord.from_dict(item) for item in list(payload.get("products", []) or [])]
        state.criteria = [CriterionRecord.from_dict(item) for item in list(payload.get("criteria", []) or [])]
        state.cells = {}
        for cell in list(payload.get("cells", []) or []):
            product_id = str(cell.get("product_id", ""))
            criterion_id = str(cell.get("criterion_id", ""))
            if product_id and criterion_id:
                state.cells[(product_id, criterion_id)] = str(cell.get("value", ""))
        vision_cache = dict(payload.get("vision_cache", {}) or {})
        for product in state.products:
            if product.id in vision_cache:
                product.vision_cache = VisionCache.from_dict(dict(vision_cache[product.id] or {}))
                product.vision_status = product.vision_cache.status
                product.vision_summary = product.vision_cache.summary
        settings = dict(payload.get("settings", {}) or {})
        state.ollama_host = str(settings.get("ollama_host", state.ollama_host))
        state.vision_model = str(settings.get("vision_model", state.vision_model))
        state.classifier_model = str(settings.get("classifier_model", state.classifier_model))
        state.project_path = project_path
        state.selected_product_id = state.products[0].id if state.products else None
        state.selected_criterion_id = state.criteria[0].id if state.criteria else None
