from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image

from features.versus_up.versus_up_state import (
    CriterionRecord,
    ProductRecord,
    ProjectMeta,
    VersusUpState,
    VisionCache,
    VisionProposal,
    utc_now_iso,
)


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


def _safe_float(value: str) -> float | None:
    try:
        return float(str(value).strip())
    except Exception:
        return None


class VersusUpService:
    def __init__(self) -> None:
        self.state = VersusUpState()
        self.app_data_dir = Path(os.environ.get("APPDATA", ".")) / "Contexthub" / "VersusUp"
        self.projects_dir = self.app_data_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.recent_file = self.app_data_dir / "recent_projects.json"
        self.presets_file = self.app_data_dir / "presets.json"
        self.settings_file = self.app_data_dir / "settings.json"
        self._presets_cache: list[dict[str, Any]] = []
        self.load_settings()
        self._load_recent_projects()
        self._load_presets()
        self.create_default_project()

    def load_settings(self) -> None:
        if not self.settings_file.exists():
            return
        try:
            data = json.loads(self.settings_file.read_text(encoding="utf-8"))
        except Exception:
            return
        self.state.ollama_host = str(data.get("ollama_host", self.state.ollama_host))
        self.state.vision_model = str(data.get("vision_model", self.state.vision_model))
        self.state.classifier_model = str(data.get("classifier_model", self.state.classifier_model))
        output_dir = str(data.get("output_dir", "")).strip()
        self.state.output_options.output_dir = Path(output_dir) if output_dir else None
        self.state.output_options.file_prefix = str(data.get("file_prefix", self.state.output_options.file_prefix))

    def save_settings(self) -> None:
        payload = {
            "ollama_host": self.state.ollama_host,
            "vision_model": self.state.vision_model,
            "classifier_model": self.state.classifier_model,
            "output_dir": str(self.state.output_options.output_dir) if self.state.output_options.output_dir else "",
            "file_prefix": self.state.output_options.file_prefix,
        }
        self.settings_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_recent_projects(self) -> None:
        if not self.recent_file.exists():
            self.state.recent_projects = []
            return
        try:
            data = json.loads(self.recent_file.read_text(encoding="utf-8"))
            self.state.recent_projects = [str(item) for item in data.get("recent_projects", []) if str(item)]
        except Exception:
            self.state.recent_projects = []

    def _save_recent_projects(self) -> None:
        unique = []
        for path in self.state.recent_projects:
            if path not in unique:
                unique.append(path)
        self.state.recent_projects = unique[:12]
        self.recent_file.write_text(
            json.dumps({"recent_projects": self.state.recent_projects}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_presets(self) -> None:
        if not self.presets_file.exists():
            self._presets_cache = []
            return
        try:
            payload = json.loads(self.presets_file.read_text(encoding="utf-8"))
            self._presets_cache = list(payload.get("presets", []) or [])
        except Exception:
            self._presets_cache = []

    def _save_presets(self) -> None:
        self.presets_file.write_text(
            json.dumps({"presets": self._presets_cache}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

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
        self.state.schema_version = str(payload.get("schema_version", "2.0"))
        self.state.project_meta = ProjectMeta.from_dict(dict(payload.get("project", {}) or {}))
        self.state.products = [ProductRecord.from_dict(item) for item in list(payload.get("products", []) or [])]
        self.state.criteria = [CriterionRecord.from_dict(item) for item in list(payload.get("criteria", []) or [])]
        self.state.cells = {}
        for cell in list(payload.get("cells", []) or []):
            product_id = str(cell.get("product_id", ""))
            criterion_id = str(cell.get("criterion_id", ""))
            if product_id and criterion_id:
                self.state.cells[(product_id, criterion_id)] = str(cell.get("value", ""))
        vision_cache = dict(payload.get("vision_cache", {}) or {})
        for product in self.state.products:
            if product.id in vision_cache:
                product.vision_cache = VisionCache.from_dict(dict(vision_cache[product.id] or {}))
                product.vision_status = product.vision_cache.status
                product.vision_summary = product.vision_cache.summary
        settings = dict(payload.get("settings", {}) or {})
        self.state.ollama_host = str(settings.get("ollama_host", self.state.ollama_host))
        self.state.vision_model = str(settings.get("vision_model", self.state.vision_model))
        self.state.classifier_model = str(settings.get("classifier_model", self.state.classifier_model))
        self.state.project_path = project_path
        self.state.selected_product_id = self.state.products[0].id if self.state.products else None
        self.state.selected_criterion_id = self.state.criteria[0].id if self.state.criteria else None
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
        scores = {product.id: 0.0 for product in self.state.products}
        reasons = {product.id: [] for product in self.state.products}
        for criterion in self.state.criteria:
            if criterion.type != "number" or not criterion.include_in_score:
                continue
            numeric_values: list[tuple[str, float]] = []
            for product in self.state.products:
                value = _safe_float(self.cell_value(product.id, criterion.id))
                if value is not None:
                    numeric_values.append((product.id, value))
            if not numeric_values:
                continue
            values = [item[1] for item in numeric_values]
            min_value = min(values)
            max_value = max(values)
            span = max_value - min_value
            for product_id, value in numeric_values:
                normalized = 1.0 if span == 0 else (value - min_value) / span
                if criterion.direction == "low":
                    normalized = 1.0 - normalized
                weighted = normalized * criterion.weight
                scores[product_id] += weighted
                reasons[product_id].append(f"{criterion.label}: {value}{criterion.unit} -> {weighted:.2f}")
        self.state.scores = scores
        self.state.score_reasons = reasons

    def best_product_id(self) -> str | None:
        if not self.state.products:
            return None
        return max(self.state.products, key=lambda product: self.state.scores.get(product.id, 0.0)).id

    def infer_value_type(self, value: str) -> str:
        return "number" if _safe_float(value) is not None else "text"

    def analyze_product_image(self, product_id: str) -> VisionCache:
        product = self.product_by_id(product_id)
        if product is None:
            raise ValueError("Unknown product")
        image_path = Path(product.image_path)
        if not image_path.exists():
            raise FileNotFoundError("Product image is missing")
        image_hash = self._hash_file(image_path)
        if product.vision_cache.image_hash == image_hash and product.vision_cache.status == "ready":
            return product.vision_cache

        product.vision_status = "running"
        product.vision_cache.status = "running"
        extracted = self._call_vision_model(image_path)
        proposals = self._classify_extracted_items(extracted)
        cache = VisionCache(
            image_hash=image_hash,
            status="ready",
            summary=str(extracted.get("summary", "")),
            raw_text=str(extracted.get("raw_text", "")),
            extracted_items=list(extracted.get("items", []) or []),
            proposals=proposals,
            analyzed_at=utc_now_iso(),
        )
        product.vision_cache = cache
        product.vision_status = cache.status
        product.vision_summary = cache.summary
        self.touch_updated_at()
        return cache

    def set_vision_error(self, product_id: str, message: str) -> None:
        product = self.product_by_id(product_id)
        if product is None:
            return
        product.vision_cache.status = "error"
        product.vision_cache.error = message
        product.vision_cache.summary = ""
        product.vision_status = "error"
        product.vision_summary = ""

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _prepare_image(self, image_path: Path, max_size: tuple[int, int] = (1400, 1400)) -> str:
        with Image.open(image_path) as img:
            img.thumbnail(max_size)
            if img.mode != "RGB":
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=88)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _post_ollama(self, payload: dict[str, Any], timeout: int = 90) -> dict[str, Any]:
        response = requests.post(f"{self.state.ollama_host}/api/generate", json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def _extract_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if "```" in cleaned:
            parts = cleaned.split("```")
            for part in parts:
                candidate = part.strip()
                if candidate.startswith("json"):
                    candidate = candidate[4:].strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    cleaned = candidate
                    break
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= start:
            cleaned = cleaned[start : end + 1]
        return json.loads(cleaned)

    def _call_vision_model(self, image_path: Path) -> dict[str, Any]:
        prompt = (
            "You are analyzing a shopping product detail screenshot. "
            "Extract OCR text and candidate specifications. "
            "Return JSON only with keys summary, raw_text, items. "
            "Each item must include name, value, unit, reason."
        )
        payload = {
            "model": self.state.vision_model,
            "prompt": prompt,
            "images": [self._prepare_image(image_path)],
            "stream": False,
            "format": "json",
        }
        result = self._post_ollama(payload)
        output = self._extract_json(str(result.get("response", "{}")))
        if "items" not in output:
            output["items"] = []
        return output

    def _classify_extracted_items(self, extracted: dict[str, Any]) -> list[VisionProposal]:
        criteria_payload = [
            {
                "id": criterion.id,
                "label": criterion.label,
                "type": criterion.type,
                "unit": criterion.unit,
            }
            for criterion in self.state.criteria
        ]
        prompt = (
            "Map extracted shopping specs to existing comparison criteria. "
            "Return JSON only with key proposals. "
            "Each proposal must include criterion_id, criterion_name, value, unit, confidence, reason, action. "
            "Use action replace for existing criteria and add for new criteria. "
            "If no good match exists, set criterion_id to null and action to add."
        )
        payload = {
            "model": self.state.classifier_model or self.state.vision_model,
            "prompt": json.dumps(
                {
                    "instruction": prompt,
                    "criteria": criteria_payload,
                    "extracted_items": extracted.get("items", []),
                },
                ensure_ascii=False,
            ),
            "stream": False,
            "format": "json",
        }
        try:
            result = self._post_ollama(payload, timeout=60)
            output = self._extract_json(str(result.get("response", "{}")))
            proposals = [VisionProposal.from_dict(item) for item in list(output.get("proposals", []) or [])]
            if proposals:
                return proposals
        except Exception:
            pass

        proposals: list[VisionProposal] = []
        for item in list(extracted.get("items", []) or []):
            name = str(item.get("name", "")).strip()
            value = str(item.get("value", "")).strip()
            unit = str(item.get("unit", "")).strip()
            best = self._match_existing_criterion(name, unit)
            proposals.append(
                VisionProposal(
                    criterion_id=best.id if best else None,
                    criterion_name=best.label if best else name,
                    value=value,
                    unit=unit,
                    confidence=0.55 if best else 0.35,
                    reason=str(item.get("reason", "Fallback keyword matching")),
                    action="replace" if best else "add",
                )
            )
        return proposals

    def _match_existing_criterion(self, name: str, unit: str) -> CriterionRecord | None:
        lowered = name.lower()
        best: CriterionRecord | None = None
        best_score = 0
        for criterion in self.state.criteria:
            score = 0
            label = criterion.label.lower()
            if lowered == label:
                score += 4
            if lowered in label or label in lowered:
                score += 2
            if unit and criterion.unit and unit.lower() == criterion.unit.lower():
                score += 2
            if score > best_score:
                best = criterion
                best_score = score
        return best

    def apply_vision_proposals(self, product_id: str, proposals: list[VisionProposal]) -> list[str]:
        applied: list[str] = []
        for proposal in proposals:
            if not proposal.approved:
                continue
            criterion_id = proposal.criterion_id
            if proposal.action == "add" or criterion_id is None or self.criterion_by_id(criterion_id) is None:
                created = self.add_criterion(
                    proposal.criterion_name,
                    description="Added from Vision proposal.",
                    data_type=self.infer_value_type(proposal.value),
                    unit=proposal.unit,
                    include_in_score=self.infer_value_type(proposal.value) == "number",
                )
                criterion_id = created.id
            self.set_cell_value(product_id, criterion_id, proposal.value)
            applied.append(f"{proposal.criterion_name}={proposal.value}{proposal.unit}")
            proposal.approved = True
        product = self.product_by_id(product_id)
        if product:
            product.vision_cache.proposals = proposals
            product.vision_status = "ready"
        self.recalculate_scores()
        self.autosave_project()
        return applied

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
