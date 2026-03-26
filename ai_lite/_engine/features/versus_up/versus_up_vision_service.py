from __future__ import annotations

import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image

from features.versus_up.versus_up_state import VisionCache, VisionProposal, utc_now_iso


class VersusUpVisionService:
    def __init__(self, state_provider, criterion_lookup, criterion_creator, cell_setter, score_recalc, autosave, infer_value_type) -> None:
        self._state = state_provider
        self._criterion_by_id = criterion_lookup
        self._add_criterion = criterion_creator
        self._set_cell_value = cell_setter
        self._recalculate_scores = score_recalc
        self._autosave_project = autosave
        self._infer_value_type = infer_value_type

    def analyze_product_image(self, product, criteria: list) -> VisionCache:
        image_path = Path(product.image_path)
        if not image_path.exists():
            raise FileNotFoundError("Product image is missing")
        image_hash = self._hash_file(image_path)
        if product.vision_cache.image_hash == image_hash and product.vision_cache.status == "ready":
            return product.vision_cache

        product.vision_status = "running"
        product.vision_cache.status = "running"
        extracted = self._call_vision_model(image_path)
        proposals = self._classify_extracted_items(criteria, extracted)
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
        return cache

    def set_vision_error(self, product, message: str) -> None:
        product.vision_cache.status = "error"
        product.vision_cache.error = message
        product.vision_cache.summary = ""
        product.vision_status = "error"
        product.vision_summary = ""

    def apply_vision_proposals(self, product_id: str, product, proposals: list[VisionProposal]) -> list[str]:
        applied: list[str] = []
        for proposal in proposals:
            if not proposal.approved:
                continue
            criterion_id = proposal.criterion_id
            if proposal.action == "add" or criterion_id is None or self._criterion_by_id(criterion_id) is None:
                created = self._add_criterion(
                    proposal.criterion_name,
                    description="Added from Vision proposal.",
                    data_type=self._infer_value_type(proposal.value),
                    unit=proposal.unit,
                    include_in_score=self._infer_value_type(proposal.value) == "number",
                )
                criterion_id = created.id
            self._set_cell_value(product_id, criterion_id, proposal.value)
            applied.append(f"{proposal.criterion_name}={proposal.value}{proposal.unit}")
            proposal.approved = True
        if product:
            product.vision_cache.proposals = proposals
            product.vision_status = "ready"
        self._recalculate_scores()
        self._autosave_project()
        return applied

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
        response = requests.post(f"{self._state().ollama_host}/api/generate", json=payload, timeout=timeout)
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
            "model": self._state().vision_model,
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

    def _classify_extracted_items(self, criteria: list, extracted: dict[str, Any]) -> list[VisionProposal]:
        criteria_payload = [{"id": criterion.id, "label": criterion.label, "type": criterion.type, "unit": criterion.unit} for criterion in criteria]
        prompt = (
            "Map extracted shopping specs to existing comparison criteria. "
            "Return JSON only with key proposals. "
            "Each proposal must include criterion_id, criterion_name, value, unit, confidence, reason, action. "
            "Use action replace for existing criteria and add for new criteria. "
            "If no good match exists, set criterion_id to null and action to add."
        )
        payload = {
            "model": self._state().classifier_model or self._state().vision_model,
            "prompt": json.dumps({"instruction": prompt, "criteria": criteria_payload, "extracted_items": extracted.get("items", [])}, ensure_ascii=False),
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
            best = self._match_existing_criterion(criteria, name, unit)
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

    def _match_existing_criterion(self, criteria: list, name: str, unit: str):
        lowered = name.lower()
        best = None
        best_score = 0
        for criterion in criteria:
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
