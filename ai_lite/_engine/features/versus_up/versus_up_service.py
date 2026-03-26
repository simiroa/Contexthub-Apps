from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from features.versus_up.versus_up_preset_store import VersusUpPresetStore
from features.versus_up.versus_up_project_store import VersusUpProjectStore
from features.versus_up.versus_up_scoring_service import VersusUpScoringService, safe_float
from features.versus_up.versus_up_settings_service import VersusUpSettingsService
from features.versus_up.versus_up_state import (
    CriterionRecord,
    ProductRecord,
    ProjectMeta,
    VersusUpState,
    VisionCache,
    VisionProposal,
    utc_now_iso,
)
from features.versus_up.versus_up_vision_service import VersusUpVisionService


PROJECT_EXTENSION = ".versusup.json"
PROJECT_TEMPLATES = {
    "cpu": {
        "name": "CPU Compare",
        "category": "Hardware",
        "products": ["Ryzen 7", "Core i7"],
        "criteria": [
            {"label": "Price", "description": "Lower is better.", "type": "number", "weight": 1.4, "direction": "low", "unit": "$"},
            {"label": "Cores", "description": "More cores are better.", "type": "number", "weight": 1.3, "direction": "high", "unit": ""},
            {"label": "Boost Clock", "description": "Higher max frequency is better.", "type": "number", "weight": 1.1, "direction": "high", "unit": "GHz"},
            {"label": "TDP", "description": "Lower power draw is preferred.", "type": "number", "weight": 0.8, "direction": "low", "unit": "W"},
        ],
    },
    "gpu": {
        "name": "GPU Compare",
        "category": "Hardware",
        "products": ["RTX 5070", "RX 9070 XT"],
        "criteria": [
            {"label": "Price", "description": "Lower is better.", "type": "number", "weight": 1.4, "direction": "low", "unit": "$"},
            {"label": "VRAM", "description": "More memory is better for large workloads.", "type": "number", "weight": 1.2, "direction": "high", "unit": "GB"},
            {"label": "Raster FPS", "description": "Higher average FPS is better.", "type": "number", "weight": 1.5, "direction": "high", "unit": "fps"},
            {"label": "Power", "description": "Lower board power is preferred.", "type": "number", "weight": 0.7, "direction": "low", "unit": "W"},
        ],
    },
    "laptop": {
        "name": "Laptop Compare",
        "category": "Mobile Computing",
        "products": ["Model A", "Model B"],
        "criteria": [
            {"label": "Price", "description": "Lower is better.", "type": "number", "weight": 1.4, "direction": "low", "unit": "$"},
            {"label": "Weight", "description": "Lighter is easier to carry.", "type": "number", "weight": 1.0, "direction": "low", "unit": "kg"},
            {"label": "Battery", "description": "Longer runtime is better.", "type": "number", "weight": 1.3, "direction": "high", "unit": "hr"},
            {"label": "Display", "description": "Qualitative notes for panel quality.", "type": "text", "weight": 0.0, "direction": "high", "unit": "", "include_in_score": False},
        ],
    },
}


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class VersusUpService:
    def __init__(self) -> None:
        self.state = VersusUpState()
        self.app_data_dir = Path(os.environ.get("APPDATA", ".")) / "Contexthub" / "VersusUp"
        self.projects_dir = self.app_data_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.recent_file = self.app_data_dir / "recent_projects.json"
        self.presets_file = self.app_data_dir / "presets.json"
        self.settings_file = self.app_data_dir / "settings.json"
        self._settings_service = VersusUpSettingsService()
        self._project_store = VersusUpProjectStore()
        self._preset_store = VersusUpPresetStore()
        self._scoring_service = VersusUpScoringService()
        self._vision_service = VersusUpVisionService(
            lambda: self.state,
            self.criterion_by_id,
            self.add_criterion,
            self.set_cell_value,
            self.recalculate_scores,
            self.autosave_project,
            self.infer_value_type,
        )
        self._presets_cache: list[dict[str, Any]] = []
        self.load_settings()
        self._load_recent_projects()
        self._load_presets()
        self.create_default_project()

    def load_settings(self) -> None:
        self._settings_service.load_settings(self.settings_file, self.state)

    def save_settings(self) -> None:
        self._settings_service.save_settings(self.settings_file, self.state)

    def _load_recent_projects(self) -> None:
        self.state.recent_projects = self._project_store.load_recent_projects(self.recent_file)

    def _save_recent_projects(self) -> None:
        self.state.recent_projects = self._project_store.save_recent_projects(self.recent_file, self.state.recent_projects)

    def _load_presets(self) -> None:
        self._presets_cache = self._preset_store.load(self.presets_file)

    def _save_presets(self) -> None:
        self._preset_store.save(self.presets_file, self._presets_cache)

    def touch_updated_at(self) -> None:
        self.state.project_meta.updated_at = utc_now_iso()

    def create_default_project(self) -> None:
        self.create_project_from_template("laptop")

    def get_template_options(self) -> list[tuple[str, str]]:
        options = [("cpu", "CPU"), ("gpu", "GPU"), ("laptop", "Laptop")]
        for preset in self._presets_cache:
            options.append((f"preset:{preset.get('id', '')}", f"{preset.get('name', 'Preset')}"))
        return options

    def create_project_from_template(self, template_key: str) -> None:
        if template_key.startswith("preset:"):
            self.create_project_from_preset(template_key.split(":", 1)[1])
            return
        template = PROJECT_TEMPLATES.get(template_key, PROJECT_TEMPLATES["laptop"])
        self.state.project_meta = ProjectMeta(name=template["name"], category=template["category"], notes="")
        self.state.products = [ProductRecord(id=_new_id("product"), name=name) for name in template["products"]]
        self.state.criteria = []
        for criterion in template["criteria"]:
            self.state.criteria.append(
                CriterionRecord(
                    id=_new_id("criterion"),
                    label=str(criterion["label"]),
                    description=str(criterion.get("description", "")),
                    type=str(criterion.get("type", "number")),
                    weight=float(criterion.get("weight", 1.0)),
                    direction=str(criterion.get("direction", "high")),
                    unit=str(criterion.get("unit", "")),
                    include_in_score=bool(criterion.get("include_in_score", criterion.get("type", "number") == "number")),
                )
            )
        self.state.cells = {}
        self.state.project_path = None
        self.state.selected_product_id = self.state.products[0].id if self.state.products else None
        self.state.selected_criterion_id = self.state.criteria[0].id if self.state.criteria else None
        self.recalculate_scores()
        self.state.status_text = f"New {template['name']} template ready"

    def create_project_from_preset(self, preset_id: str) -> None:
        preset = next((item for item in self._presets_cache if str(item.get("id", "")) == preset_id), None)
        if preset is None:
            self.create_project_from_template("laptop")
            return
        self.state.project_meta = ProjectMeta(
            name=str(preset.get("name", "Preset Compare")),
            category=str(preset.get("category", "Custom Preset")),
            notes="",
        )
        product_names = list(preset.get("products", []) or []) or ["Model A", "Model B"]
        self.state.products = [ProductRecord(id=_new_id("product"), name=str(name)) for name in product_names]
        self.state.criteria = []
        for criterion in list(preset.get("criteria", []) or []):
            self.state.criteria.append(
                CriterionRecord(
                    id=_new_id("criterion"),
                    label=str(criterion.get("label", "Criterion")),
                    description=str(criterion.get("description", "")),
                    type=str(criterion.get("type", "number")),
                    weight=float(criterion.get("weight", 1.0)),
                    direction=str(criterion.get("direction", "high")),
                    unit=str(criterion.get("unit", "")),
                    include_in_score=bool(criterion.get("include_in_score", True)),
                )
            )
        self.state.cells = {}
        self.state.project_path = None
        self.state.selected_product_id = self.state.products[0].id if self.state.products else None
        self.state.selected_criterion_id = self.state.criteria[0].id if self.state.criteria else None
        self.recalculate_scores()
        self.state.status_text = f"Loaded preset {preset.get('name', 'Preset')}"

    def build_project_payload(self) -> dict[str, Any]:
        cells = [
            {"product_id": product_id, "criterion_id": criterion_id, "value": value}
            for (product_id, criterion_id), value in self.state.cells.items()
        ]
        return {
            "schema_version": self.state.schema_version,
            "project": self.state.project_meta.to_dict(),
            "products": [product.to_dict() for product in self.state.products],
            "criteria": [criterion.to_dict() for criterion in self.state.criteria],
            "cells": cells,
            "vision_cache": {product.id: product.vision_cache.to_dict() for product in self.state.products},
            "settings": {
                "ollama_host": self.state.ollama_host,
                "vision_model": self.state.vision_model,
                "classifier_model": self.state.classifier_model,
            },
        }

    def apply_project_payload(self, payload: dict[str, Any], project_path: Path | None = None) -> None:
        self._project_store.apply_project_payload(self.state, payload, project_path)
        self.recalculate_scores()
        self.state.status_text = f"Loaded {self.state.project_meta.name}"

    def _slugify(self, name: str) -> str:
        chars = []
        for char in name.lower():
            if char.isalnum():
                chars.append(char)
            elif chars and chars[-1] != "_":
                chars.append("_")
        return "".join(chars).strip("_") or "versus_up"

    def suggested_project_path(self) -> Path:
        if self.state.project_path is not None:
            return self.state.project_path
        return self.unique_project_path(self.state.project_meta.name)

    def unique_project_path(self, name: str, *, exclude: Path | None = None) -> Path:
        base = self.projects_dir / f"{self._slugify(name)}{PROJECT_EXTENSION}"
        if not base.exists() or (exclude and base == exclude):
            return base
        index = 2
        while True:
            candidate = self.projects_dir / f"{self._slugify(name)}_{index}{PROJECT_EXTENSION}"
            if not candidate.exists() or (exclude and candidate == exclude):
                return candidate
            index += 1

    def save_project(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.suggested_project_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        self.touch_updated_at()
        target.write_text(json.dumps(self.build_project_payload(), indent=2, ensure_ascii=False), encoding="utf-8")
        self.state.project_path = target
        self._remember_recent_project(target)
        self.save_settings()
        self.state.status_text = f"Saved project to {target.name}"
        return target

    def autosave_project(self) -> Path | None:
        try:
            target = self.save_project(self.state.project_path or self.unique_project_path(self.state.project_meta.name))
            self.state.status_text = f"Saved automatically: {target.name}"
            return target
        except Exception as exc:
            self.state.status_text = f"Autosave failed: {exc}"
            return None

    def ensure_project_registered(self) -> Path:
        target = self.state.project_path or self.unique_project_path(self.state.project_meta.name)
        if not target.exists():
            return self.save_project(target)
        self.state.project_path = target
        self._remember_recent_project(target)
        return target

    def load_project(self, path: str | Path) -> None:
        project_path = Path(path)
        payload = json.loads(project_path.read_text(encoding="utf-8"))
        self.apply_project_payload(payload, project_path)
        self._remember_recent_project(project_path)

    def _remember_recent_project(self, path: Path) -> None:
        text = str(path)
        self.state.recent_projects = [text] + [item for item in self.state.recent_projects if item != text]
        self._save_recent_projects()

    def recent_project_entries(self) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        for raw_path in self.state.recent_projects:
            path = Path(raw_path)
            name = path.stem.replace(PROJECT_EXTENSION.replace(".json", ""), "").strip("._-") or path.stem
            category = ""
            if path.exists():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    project = dict(payload.get("project", {}) or {})
                    name = str(project.get("name", name))
                    category = str(project.get("category", ""))
                except Exception:
                    category = ""
            entries.append({"path": raw_path, "name": name, "category": category})
        return entries

    def preset_entries(self) -> list[dict[str, str]]:
        return [
            {
                "id": str(item.get("id", "")),
                "name": str(item.get("name", "Preset")),
                "category": str(item.get("category", "")),
            }
            for item in self._presets_cache
        ]

    def save_current_as_preset(self, name: str) -> str:
        preset_name = name.strip()
        if not preset_name:
            raise ValueError("Preset name cannot be empty.")
        preset_id = self._slugify(preset_name)
        criteria_payload = [
            {
                "label": criterion.label,
                "description": criterion.description,
                "type": criterion.type,
                "weight": criterion.weight,
                "direction": criterion.direction,
                "unit": criterion.unit,
                "include_in_score": criterion.include_in_score,
            }
            for criterion in self.state.criteria
        ]
        payload = {
            "id": preset_id,
            "name": preset_name,
            "category": self.state.project_meta.category,
            "products": [product.name for product in self.state.products],
            "criteria": criteria_payload,
        }
        self._presets_cache = [item for item in self._presets_cache if str(item.get("id", "")) != preset_id]
        self._presets_cache.insert(0, payload)
        self._save_presets()
        self.state.status_text = f"Preset saved: {preset_name}"
        return preset_id

    def delete_preset(self, preset_id: str) -> None:
        before = len(self._presets_cache)
        self._presets_cache = [item for item in self._presets_cache if str(item.get("id", "")) != preset_id]
        if len(self._presets_cache) != before:
            self._save_presets()
            self.state.status_text = "Preset removed"

    def rename_current_project(self, new_name: str) -> Path:
        cleaned = new_name.strip()
        if not cleaned:
            raise ValueError("Project name cannot be empty.")
        current_path = self.state.project_path
        self.state.project_meta.name = cleaned
        if current_path and current_path.exists():
            target = self.unique_project_path(cleaned, exclude=current_path)
            self.touch_updated_at()
            current_path.replace(target)
            self.state.project_path = target
            target.write_text(json.dumps(self.build_project_payload(), indent=2, ensure_ascii=False), encoding="utf-8")
            self.state.recent_projects = [str(target) if item == str(current_path) else item for item in self.state.recent_projects]
            self._save_recent_projects()
            self.state.status_text = f"Renamed project to {target.name}"
            return target
        target = self.save_project(self.unique_project_path(cleaned))
        self.state.status_text = f"Renamed project to {target.name}"
        return target

    def duplicate_current_project(self, new_name: str | None = None) -> Path:
        duplicate_name = (new_name or f"{self.state.project_meta.name} Copy").strip()
        if not duplicate_name:
            duplicate_name = f"{self.state.project_meta.name} Copy"
        self.state.project_meta.name = duplicate_name
        target = self.save_project(self.unique_project_path(duplicate_name))
        self.state.status_text = f"Duplicated project as {target.name}"
        return target

    def export_report(self, path: str | Path | None = None) -> Path:
        output_dir = self.resolve_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        target = Path(path) if path else output_dir / f"{self.state.output_options.file_prefix}_report.md"
        lines = [
            f"# {self.state.project_meta.name}",
            "",
            f"- Category: {self.state.project_meta.category}",
            f"- Updated: {self.state.project_meta.updated_at}",
            "",
            "## Ranking",
            "",
        ]
        for rank, product in enumerate(self.sorted_products(), start=1):
            score = self.state.scores.get(product.id, 0.0)
            lines.append(f"{rank}. **{product.name}** - {score:.3f}")
            for reason in self.state.score_reasons.get(product.id, [])[:3]:
                lines.append(f"   - {reason}")
        lines.extend(["", "## Matrix", ""])
        header = ["Criterion"] + [product.name for product in self.state.products]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for criterion in self.state.criteria:
            row = [criterion.label]
            for product in self.state.products:
                row.append(self.cell_value(product.id, criterion.id))
            lines.append("| " + " | ".join(row) + " |")
        target.write_text("\n".join(lines), encoding="utf-8")
        self.state.status_text = f"Exported report to {target.name}"
        return target

    def resolve_output_dir(self) -> Path:
        if self.state.output_options.output_dir:
            return self.state.output_options.output_dir
        if self.state.project_path:
            return self.state.project_path.parent
        return self.projects_dir

    def reveal_output_dir(self) -> None:
        path = self.resolve_output_dir()
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)

    def open_path(self, path: Path) -> None:
        if os.name == "nt":
            os.startfile(path)

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir) if output_dir.strip() else None
        self.state.output_options.file_prefix = file_prefix.strip() or "versus_up"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json
        self.save_settings()

    def set_project_meta(self, name: str | None = None, category: str | None = None, notes: str | None = None) -> None:
        if name is not None:
            self.state.project_meta.name = name
        if category is not None:
            self.state.project_meta.category = category
        if notes is not None:
            self.state.project_meta.notes = notes
        self.touch_updated_at()
        self.autosave_project()

    def sorted_products(self) -> list[ProductRecord]:
        return sorted(
            self.state.products,
            key=lambda item: (0 if item.favorite else 1, -self.state.scores.get(item.id, 0.0), item.name.lower()),
        )

    def product_by_id(self, product_id: str | None) -> ProductRecord | None:
        if not product_id:
            return None
        for product in self.state.products:
            if product.id == product_id:
                return product
        return None

    def criterion_by_id(self, criterion_id: str | None) -> CriterionRecord | None:
        if not criterion_id:
            return None
        for criterion in self.state.criteria:
            if criterion.id == criterion_id:
                return criterion
        return None

    def cell_value(self, product_id: str, criterion_id: str) -> str:
        return self.state.cells.get((product_id, criterion_id), "")

    def set_cell_value(self, product_id: str, criterion_id: str, value: str) -> None:
        self.state.cells[(product_id, criterion_id)] = value
        self.touch_updated_at()
        self.autosave_project()

    def add_product(self, name: str | None = None) -> ProductRecord:
        product = ProductRecord(id=_new_id("product"), name=name or f"Model {len(self.state.products) + 1}")
        self.state.products.append(product)
        self.state.selected_product_id = product.id
        self.touch_updated_at()
        self.recalculate_scores()
        self.autosave_project()
        return product

    def remove_product(self, product_id: str) -> None:
        self.state.products = [product for product in self.state.products if product.id != product_id]
        self.state.cells = {(pid, cid): value for (pid, cid), value in self.state.cells.items() if pid != product_id}
        if self.state.selected_product_id == product_id:
            self.state.selected_product_id = self.state.products[0].id if self.state.products else None
        self.touch_updated_at()
        self.recalculate_scores()
        self.autosave_project()

    def update_product(
        self,
        product_id: str,
        *,
        name: str | None = None,
        favorite: bool | None = None,
        color: str | None = None,
        image_path: str | None = None,
        image_paths: list[str] | None = None,
        notes: str | None = None,
    ) -> None:
        product = self.product_by_id(product_id)
        if product is None:
            return
        if name is not None:
            product.name = name
        if favorite is not None:
            product.favorite = favorite
        if color is not None:
            product.color = color
        if image_paths is not None:
            normalized = [str(path) for path in image_paths if str(path).strip()]
            if normalized != product.image_paths:
                product.vision_cache = VisionCache()
                product.vision_status = "idle"
                product.vision_summary = ""
            product.image_paths = normalized
            product.image_path = normalized[0] if normalized else ""
        if image_path is not None:
            if product.image_path != image_path:
                product.vision_cache = VisionCache()
                product.vision_status = "idle"
                product.vision_summary = ""
            product.image_path = image_path
            if image_path:
                product.image_paths = [image_path] + [path for path in product.image_paths if path != image_path]
            else:
                product.image_paths = []
        if notes is not None:
            product.notes = notes
        self.touch_updated_at()
        self.autosave_project()

    def attach_product_images(self, product_id: str, paths: list[str]) -> None:
        product = self.product_by_id(product_id)
        if product is None:
            return
        merged = list(product.image_paths)
        changed = False
        for path in paths:
            normalized = str(path).strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
                changed = True
        if not merged:
            return
        if not product.image_path:
            product.image_path = merged[0]
            changed = True
        if changed:
            self.update_product(product_id, image_path=product.image_path, image_paths=merged)

    def set_main_product_image(self, product_id: str, path: str) -> None:
        product = self.product_by_id(product_id)
        if product is None:
            return
        normalized = str(path).strip()
        merged = [normalized] + [item for item in product.image_paths if item != normalized]
        self.update_product(product_id, image_path=normalized, image_paths=merged)

    def remove_product_image(self, product_id: str, path: str) -> None:
        product = self.product_by_id(product_id)
        if product is None:
            return
        normalized = str(path).strip()
        merged = [item for item in product.image_paths if item != normalized]
        main_path = merged[0] if merged else ""
        self.update_product(product_id, image_path=main_path, image_paths=merged)

    def add_criterion(
        self,
        label: str | None = None,
        *,
        data_type: str = "number",
        weight: float = 1.0,
        direction: str = "high",
        unit: str = "",
        description: str = "",
        include_in_score: bool | None = None,
    ) -> CriterionRecord:
        criterion = CriterionRecord(
            id=_new_id("criterion"),
            label=label or f"Criterion {len(self.state.criteria) + 1}",
            description=description,
            type=data_type,
            weight=weight,
            direction=direction,
            unit=unit,
            include_in_score=include_in_score if include_in_score is not None else data_type == "number",
        )
        self.state.criteria.append(criterion)
        self.state.selected_criterion_id = criterion.id
        self.touch_updated_at()
        self.recalculate_scores()
        self.autosave_project()
        return criterion

    def remove_criterion(self, criterion_id: str) -> None:
        self.state.criteria = [criterion for criterion in self.state.criteria if criterion.id != criterion_id]
        self.state.cells = {(pid, cid): value for (pid, cid), value in self.state.cells.items() if cid != criterion_id}
        if self.state.selected_criterion_id == criterion_id:
            self.state.selected_criterion_id = self.state.criteria[0].id if self.state.criteria else None
        self.touch_updated_at()
        self.recalculate_scores()
        self.autosave_project()

    def update_criterion(
        self,
        criterion_id: str,
        *,
        label: str | None = None,
        description: str | None = None,
        data_type: str | None = None,
        weight: float | None = None,
        direction: str | None = None,
        unit: str | None = None,
        include_in_score: bool | None = None,
    ) -> None:
        criterion = self.criterion_by_id(criterion_id)
        if criterion is None:
            return
        if label is not None:
            criterion.label = label
        if description is not None:
            criterion.description = description
        if data_type is not None:
            criterion.type = data_type
        if weight is not None:
            criterion.weight = weight
        if direction is not None:
            criterion.direction = direction
        if unit is not None:
            criterion.unit = unit
        if include_in_score is not None:
            criterion.include_in_score = include_in_score
        self.touch_updated_at()
        self.recalculate_scores()
        self.autosave_project()

    def select_cell(self, row: int, column: int) -> None:
        if 0 <= row < len(self.state.criteria):
            self.state.selected_criterion_id = self.state.criteria[row].id
        if 0 <= column < len(self.state.products):
            self.state.selected_product_id = self.state.products[column].id

    def recalculate_scores(self) -> None:
        self._scoring_service.recalculate_scores(self.state, self.cell_value)

    def best_product_id(self) -> str | None:
        if not self.state.products:
            return None
        return max(self.state.products, key=lambda product: self.state.scores.get(product.id, 0.0)).id

    def infer_value_type(self, value: str) -> str:
        return "number" if safe_float(value) is not None else "text"

    def analyze_product_image(self, product_id: str) -> VisionCache:
        product = self.product_by_id(product_id)
        if product is None:
            raise ValueError("Unknown product")
        cache = self._vision_service.analyze_product_image(product, self.state.criteria)
        self.touch_updated_at()
        return cache

    def set_vision_error(self, product_id: str, message: str) -> None:
        product = self.product_by_id(product_id)
        if product is None:
            return
        self._vision_service.set_vision_error(product, message)

    def apply_vision_proposals(self, product_id: str, proposals: list[VisionProposal]) -> list[str]:
        product = self.product_by_id(product_id)
        return self._vision_service.apply_vision_proposals(product_id, product, proposals)

    def build_runtime_status(self) -> tuple[str, str]:
        best_id = self.best_product_id()
        best_name = self.product_by_id(best_id).name if best_id else "No ranking"
        return (f"Top score: {best_name}", "ready")

    def run_primary_action(self) -> tuple[bool, str, Path | None]:
        save_path = self.save_project()
        if self.state.output_options.open_folder_after_run:
            self.reveal_output_dir()
        return True, f"Project saved: {save_path.name}", save_path

    def open_recent_or_default(self) -> None:
        for recent in self.state.recent_projects:
            path = Path(recent)
            if path.exists():
                self.load_project(path)
                return
        self.ensure_project_registered()

    def build_project_snapshot_json(self) -> Path:
        output_dir = self.resolve_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{self.state.output_options.file_prefix}_session.json"
        path.write_text(json.dumps(self.build_project_payload(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path
