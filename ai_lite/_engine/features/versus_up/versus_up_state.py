from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class VisionProposal:
    criterion_id: str | None
    criterion_name: str
    value: str
    unit: str = ""
    confidence: float = 0.0
    reason: str = ""
    action: str = "replace"
    approved: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "criterion_id": self.criterion_id,
            "criterion_name": self.criterion_name,
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence,
            "reason": self.reason,
            "action": self.action,
            "approved": self.approved,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "VisionProposal":
        return cls(
            criterion_id=str(data.get("criterion_id")) if data.get("criterion_id") is not None else None,
            criterion_name=str(data.get("criterion_name", "")),
            value=str(data.get("value", "")),
            unit=str(data.get("unit", "")),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            reason=str(data.get("reason", "")),
            action=str(data.get("action", "replace") or "replace"),
            approved=bool(data.get("approved", False)),
        )


@dataclass
class VisionCache:
    image_hash: str = ""
    status: str = "idle"
    summary: str = ""
    raw_text: str = ""
    extracted_items: list[dict[str, object]] = field(default_factory=list)
    proposals: list[VisionProposal] = field(default_factory=list)
    error: str = ""
    analyzed_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "image_hash": self.image_hash,
            "status": self.status,
            "summary": self.summary,
            "raw_text": self.raw_text,
            "extracted_items": self.extracted_items,
            "proposals": [proposal.to_dict() for proposal in self.proposals],
            "error": self.error,
            "analyzed_at": self.analyzed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "VisionCache":
        return cls(
            image_hash=str(data.get("image_hash", "")),
            status=str(data.get("status", "idle")),
            summary=str(data.get("summary", "")),
            raw_text=str(data.get("raw_text", "")),
            extracted_items=list(data.get("extracted_items", []) or []),
            proposals=[VisionProposal.from_dict(item) for item in list(data.get("proposals", []) or [])],
            error=str(data.get("error", "")),
            analyzed_at=str(data.get("analyzed_at", "")),
        )


@dataclass
class ProductRecord:
    id: str
    name: str
    favorite: bool = False
    color: str = ""
    image_path: str = ""
    image_paths: list[str] = field(default_factory=list)
    notes: str = ""
    vision_status: str = "idle"
    vision_summary: str = ""
    vision_cache: VisionCache = field(default_factory=VisionCache)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "favorite": self.favorite,
            "color": self.color,
            "image_path": self.image_path,
            "image_paths": self.image_paths,
            "notes": self.notes,
            "vision_status": self.vision_status,
            "vision_summary": self.vision_summary,
            "vision_cache": self.vision_cache.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ProductRecord":
        image_paths = [str(item) for item in list(data.get("image_paths", []) or []) if str(item).strip()]
        image_path = str(data.get("image_path", ""))
        if image_path and image_path not in image_paths:
            image_paths.insert(0, image_path)
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            favorite=bool(data.get("favorite", False)),
            color=str(data.get("color", "")),
            image_path=image_path or (image_paths[0] if image_paths else ""),
            image_paths=image_paths,
            notes=str(data.get("notes", "")),
            vision_status=str(data.get("vision_status", "idle")),
            vision_summary=str(data.get("vision_summary", "")),
            vision_cache=VisionCache.from_dict(dict(data.get("vision_cache", {}) or {})),
        )


@dataclass
class CriterionRecord:
    id: str
    label: str
    description: str = ""
    type: str = "number"
    weight: float = 1.0
    direction: str = "high"
    unit: str = ""
    include_in_score: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "type": self.type,
            "weight": self.weight,
            "direction": self.direction,
            "unit": self.unit,
            "include_in_score": self.include_in_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CriterionRecord":
        return cls(
            id=str(data.get("id", "")),
            label=str(data.get("label", "")),
            description=str(data.get("description", "")),
            type=str(data.get("type", "number")),
            weight=float(data.get("weight", 1.0) or 1.0),
            direction=str(data.get("direction", "high") or "high"),
            unit=str(data.get("unit", "")),
            include_in_score=bool(data.get("include_in_score", True)),
        )


@dataclass
class ProjectMeta:
    name: str = "Untitled Comparison"
    category: str = "General"
    notes: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "category": self.category,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ProjectMeta":
        return cls(
            name=str(data.get("name", "Untitled Comparison")),
            category=str(data.get("category", "General")),
            notes=str(data.get("notes", "")),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
        )


@dataclass
class OutputOptions:
    output_dir: Path | None = None
    file_prefix: str = "versus_up"
    open_folder_after_run: bool = True
    export_session_json: bool = False


@dataclass
class VersusUpState:
    project_meta: ProjectMeta = field(default_factory=ProjectMeta)
    project_path: Path | None = None
    products: list[ProductRecord] = field(default_factory=list)
    criteria: list[CriterionRecord] = field(default_factory=list)
    cells: dict[tuple[str, str], str] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    score_reasons: dict[str, list[str]] = field(default_factory=dict)
    selected_product_id: str | None = None
    selected_criterion_id: str | None = None
    status_text: str = "Ready"
    runtime_status: str = "Idle"
    recent_projects: list[str] = field(default_factory=list)
    output_options: OutputOptions = field(default_factory=OutputOptions)
    ollama_host: str = "http://localhost:11434"
    vision_model: str = "llava"
    classifier_model: str = "llama3.2"
    current_hover_product_id: str | None = None
    pending_vision_product_id: str | None = None
    schema_version: str = "2.0"
