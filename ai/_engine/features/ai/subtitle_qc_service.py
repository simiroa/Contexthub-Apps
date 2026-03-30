from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
try:
    import ollama
except Exception:
    ollama = None

from contexthub.ui.qt.shell import qt_t

from features.ai.subtitle_qc_state import (
    SUPPORTED_MEDIA_EXTS,
    GenerationOptions,
    InputAsset,
    SubtitleDocument,
    SubtitleQcState,
    SubtitleSegment,
)
from features.ai.subtitle_qc_backend_registry import registry as backend_registry
import features.ai.subtitle_qc_backend_whisper  # noqa: F401
import features.ai.subtitle_qc_backend_cohere  # noqa: F401
from features.ai.subtitle_qc_backend_types import SubtitleGenerationRequest
from features.ai.subtitle_qc_document_logic import (
    analyze_document,
    coerce_output_formats,
    normalize_segment_payload,
    parse_transcript_text,
    to_float_timestamp,
    write_segments_to_file,
)


class SubtitleQcService:
    def __init__(self, on_update: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.state = SubtitleQcState()
        self._on_update = on_update
        self._thread: threading.Thread | None = None
        self._thread_lock = threading.Lock()

    def _emit_update(self, **payload: Any) -> None:
        if not self._on_update:
            return
        payload.setdefault("generation_status", self.state.generation_status)
        payload.setdefault("generation_status_tone", self.state.generation_status_tone)
        payload.setdefault("is_processing", self.state.is_processing)
        payload.setdefault("progress", self.state.progress)
        payload.setdefault("queue_count", len(self.state.queued_assets))
        payload.setdefault("approved_count", self.state.approved_count)
        payload.setdefault("failed_count", self.state.failed_count)
        self._on_update(payload)

    def _asset_id_for_path(self, path: Path) -> str:
        return path.resolve().as_posix()

    def _session_path_for_asset(self, path: Path) -> Path:
        return path.with_name(f"{path.stem}.subtitle_qc_session.json")

    def _find_asset(self, path: Path | None = None) -> InputAsset | None:
        target = Path(path) if path else self.state.selected_asset
        if target is None:
            return None
        for asset in self.state.queued_assets:
            if asset.path == target:
                return asset
        return None

    def _sync_counts(self) -> None:
        self.state.approved_count = sum(1 for asset in self.state.queued_assets if asset.status == "approved")
        self.state.failed_count = sum(1 for asset in self.state.queued_assets if asset.status == "failed")
        self.state.dirty_flag = any(document.dirty for document in self.state.subtitle_docs_by_path.values())

    def _autosave_document(self, asset: Path | None = None) -> None:
        if not self.state.output_options.export_session_json:
            return
        try:
            self.export_session(asset)
        except Exception:
            pass

    def add_inputs(self, paths: list[str | Path]) -> None:
        for raw in paths:
            source = Path(raw)
            if not source.exists():
                continue
            candidates: list[Path] = []
            if source.is_dir():
                candidates = [item for item in source.iterdir() if item.suffix.lower() in SUPPORTED_MEDIA_EXTS]
            elif source.suffix.lower() in SUPPORTED_MEDIA_EXTS:
                candidates = [source]
            for candidate in candidates:
                if any(asset.path == candidate for asset in self.state.queued_assets):
                    continue
                kind = "audio" if candidate.suffix.lower() in {".mp3", ".wav", ".m4a", ".flac", ".ogg"} else "video"
                asset = InputAsset(
                    asset_id=self._asset_id_for_path(candidate),
                    path=candidate,
                    kind=kind,
                    session_path=self._session_path_for_asset(candidate),
                )
                self.state.queued_assets.append(asset)
        if self.state.selected_asset is None and self.state.queued_assets:
            self.set_selected_asset(self.state.queued_assets[0].path)
        self.state.generation_status = qt_t("subtitle_qc.ready", "Ready")
        self.state.generation_status_tone = "ready"
        self._sync_counts()
        self._emit_update(type="queue")

    def remove_input_at(self, index: int) -> None:
        if not (0 <= index < len(self.state.queued_assets)):
            return
        removed = self.state.queued_assets.pop(index)
        self.state.subtitle_docs_by_path.pop(str(removed.path), None)
        if self.state.selected_asset == removed.path:
            self.state.selected_asset = self.state.queued_assets[0].path if self.state.queued_assets else None
        if self.state.selected_asset:
            self.load_session_for_asset(self.state.selected_asset)
        self._sync_counts()
        self._emit_update(type="queue")

    def clear_inputs(self) -> None:
        self.state = SubtitleQcState(
            generation_options=self.state.generation_options,
            output_options=self.state.output_options,
            review_options=self.state.review_options,
        )
        self._emit_update(type="queue")

    def set_selected_asset(self, path: str | Path | None) -> None:
        selected = Path(path) if path else None
        if selected is None or not any(asset.path == selected for asset in self.state.queued_assets):
            self.state.selected_asset = None
            self.state.current_item_session = None
            self._emit_update(type="selection")
            return
        self.state.selected_asset = selected
        self.state.current_item_session = self._session_path_for_asset(selected)
        self.load_session_for_asset(selected)
        document = self._ensure_document(selected)
        if document is not None:
            self.state.generation_options = GenerationOptions(**asdict(document.generation_options))
            self.state.review_options.offset_ms = document.offset_ms
        self._emit_update(type="selection")

    def get_selected_asset(self) -> InputAsset | None:
        return self._find_asset(self.state.selected_asset)

    def get_next_asset_path(self, current: Path | None = None) -> Path | None:
        if not self.state.queued_assets:
            return None
        target = current or self.state.selected_asset
        if target is None:
            return self.state.queued_assets[0].path
        paths = [asset.path for asset in self.state.queued_assets]
        try:
            start_index = paths.index(target)
        except ValueError:
            return paths[0]
        for offset in range(1, len(paths) + 1):
            candidate = self.state.queued_assets[(start_index + offset) % len(paths)]
            if candidate.status in {"review_ready", "needs_retry", "queued", "failed"}:
                return candidate.path
        return paths[(start_index + 1) % len(paths)] if len(paths) > 1 else target

    def _ensure_document(self, asset: Path | None = None) -> SubtitleDocument | None:
        target = asset or self.state.selected_asset
        if target is None:
            return None
        document = self.state.subtitle_docs_by_path.get(str(target))
        if document is not None:
            return document
        document = SubtitleDocument(
            asset_path=target,
            meta_file_prefix=target.stem,
            generated_formats=coerce_output_formats(self.state.generation_options.output_formats),
            generation_options=GenerationOptions(**asdict(self.state.generation_options)),
            offset_ms=self.state.review_options.offset_ms,
        )
        self.state.subtitle_docs_by_path[str(target)] = document
        return document

    def get_document(self, asset: Path | None = None) -> SubtitleDocument | None:
        target = asset or self.state.selected_asset
        if target is None:
            return None
        return self.state.subtitle_docs_by_path.get(str(target))

    def update_generation_options(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        task: str | None = None,
        device: str | None = None,
        language: str | None = None,
        output_formats: list[str] | None = None,
    ) -> None:
        options = self.state.generation_options
        if provider is not None:
            options.provider = provider
        if model is not None:
            options.model = model
        if task is not None:
            options.task = task
        if device is not None:
            options.device = device
        if language is not None:
            options.language = language
        if output_formats is not None:
            options.output_formats = coerce_output_formats(output_formats)
        self._emit_update(type="options")

    def available_generation_providers(self) -> list[str]:
        return backend_registry.ids()

    def update_output_options(self, output_dir: str, file_prefix: str, open_folder_after_run: bool, export_session_json: bool) -> None:
        options = self.state.output_options
        options.output_dir = Path(output_dir) if output_dir.strip() else None
        options.file_prefix = file_prefix.strip() or "subtitle"
        options.open_folder_after_run = bool(open_folder_after_run)
        options.export_session_json = bool(export_session_json)
        self._emit_update(type="output_options")

    def update_review_options(
        self,
        *,
        overlay_enabled: bool | None = None,
        overlay_font_percent: int | None = None,
        offset_ms: int | None = None,
        playback_rate: float | None = None,
        auto_advance_review: bool | None = None,
    ) -> None:
        options = self.state.review_options
        if overlay_enabled is not None:
            options.overlay_enabled = bool(overlay_enabled)
        if overlay_font_percent is not None:
            options.overlay_font_percent = int(overlay_font_percent)
        if offset_ms is not None:
            options.offset_ms = int(offset_ms)
            document = self.get_document()
            if document is not None:
                document.offset_ms = options.offset_ms
                document.dirty = True
                self._analyze_document(document)
                self._autosave_document(document.asset_path)
        if playback_rate is not None:
            options.playback_rate = float(playback_rate)
        if auto_advance_review is not None:
            options.auto_advance_review = bool(auto_advance_review)
        self._emit_update(type="review_options")

    def set_offset_ms(self, value: int, asset: Path | None = None) -> None:
        target = asset or self.state.selected_asset
        document = self.get_document(target)
        self.update_review_options(offset_ms=value)
        if document is not None:
            document.offset_ms = int(value)
            self._autosave_document(document.asset_path)

    def resolve_output_dir(self, asset: Path | None = None) -> Path:
        if self.state.output_options.output_dir:
            return self.state.output_options.output_dir
        target = asset or self.state.selected_asset
        if target:
            return target.parent
        return Path.cwd()

    def reveal_output_dir(self, asset: Path | None = None) -> None:
        output_dir = self.resolve_output_dir(asset)
        output_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(output_dir)

    def _write_segments_to_file(self, asset: Path, document: SubtitleDocument, fmt: str, output_dir: Path) -> str:
        stem = self.state.output_options.file_prefix.strip() or document.meta_file_prefix or asset.stem
        return write_segments_to_file(asset, document, fmt, output_dir, stem)

    def export_outputs(self, asset: Path | None = None) -> dict[str, list[str]]:
        target = asset or self.state.selected_asset
        document = self.get_document(target)
        if target is None or document is None:
            return {}
        output_dir = self.resolve_output_dir(target)
        output_paths: dict[str, list[str]] = {}
        for fmt in coerce_output_formats(self.state.generation_options.output_formats):
            output_paths.setdefault(fmt, []).append(self._write_segments_to_file(target, document, fmt, output_dir))
        document.output_paths = output_paths
        document.generated_formats = list(output_paths.keys())
        document.dirty = False
        self._autosave_document(target)
        self._emit_update(type="export")
        return output_paths

    def get_transcript_text(self, asset: Path | None = None, include_timestamps: bool = True) -> str:
        document = self.get_document(asset)
        if document is None or not document.segments:
            return ""
        rows: list[str] = []
        for segment in document.segments:
            if include_timestamps:
                rows.append(f"[{segment.start:08.3f}-{segment.end:08.3f}] {segment.text}")
            else:
                rows.append(segment.text)
        return "\n".join(rows).strip()

    def update_transcript_text(self, text: str, asset: Path | None = None) -> None:
        document = self._ensure_document(asset)
        if document is None:
            return
        document.segments = parse_transcript_text(text)
        document.dirty = True
        document.approved = False
        document.review_status = "review_ready"
        self._reindex_segments(document)
        self._analyze_document(document)
        self._update_asset_from_document(document)
        self._autosave_document(document.asset_path)
        self._emit_update(type="transcript_text")

    def get_meeting_notes(self, asset: Path | None = None) -> dict[str, str]:
        document = self.get_document(asset)
        if document is None:
            return {"summary": "", "decisions": "", "actions": "", "follow_up": ""}
        notes = document.metadata.get("meeting_notes", {})
        if not isinstance(notes, dict):
            notes = {}
        return {
            "summary": str(notes.get("summary", "")),
            "decisions": str(notes.get("decisions", "")),
            "actions": str(notes.get("actions", "")),
            "follow_up": str(notes.get("follow_up", "")),
        }

    def list_ollama_models(self) -> list[str]:
        if ollama is None:
            return []
        try:
            response = ollama.list()
            models = getattr(response, "models", None)
            if models is None and isinstance(response, dict):
                models = response.get("models", [])
            names: list[str] = []
            for item in models or []:
                name = getattr(item, "model", None)
                if name is None and isinstance(item, dict):
                    name = item.get("model") or item.get("name")
                value = str(name or "").strip()
                if value:
                    names.append(value)
            return names
        except Exception:
            return []

    def get_ai_summary(self, asset: Path | None = None) -> str:
        document = self.get_document(asset)
        if document is None:
            return ""
        return str(document.metadata.get("ai_summary", ""))

    def update_ai_summary(self, summary: str, asset: Path | None = None) -> None:
        document = self._ensure_document(asset)
        if document is None:
            return
        document.metadata["ai_summary"] = summary.strip()
        document.dirty = True
        self._autosave_document(document.asset_path)
        self._emit_update(type="ai_summary")

    def summarize_transcript_with_ollama(
        self,
        *,
        asset: Path | None = None,
        model: str,
        instruction: str | None = None,
    ) -> str:
        if ollama is None:
            raise RuntimeError("Ollama Python package is not installed.")
        document = self._ensure_document(asset)
        if document is None:
            raise RuntimeError("No meeting selected.")
        transcript = self.get_transcript_text(document.asset_path, include_timestamps=False).strip()
        if not transcript:
            raise RuntimeError("Transcript is empty.")
        system_prompt = (
            instruction.strip()
            if instruction and instruction.strip()
            else "Summarize the meeting transcript. Return concise markdown with sections: Summary, Key Points, Action Items, Risks."
        )
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript},
            ],
            stream=False,
        )
        message = getattr(response, "message", None)
        content = getattr(message, "content", None)
        if content is None and isinstance(response, dict):
            content = response.get("message", {}).get("content", "")
        content = str(content or "").strip()
        document.metadata["ai_summary"] = content
        document.metadata["ai_summary_model"] = model
        document.metadata["ai_summary_instruction"] = system_prompt
        document.dirty = True
        self._autosave_document(document.asset_path)
        self._emit_update(type="ai_summary")
        return content

    def update_meeting_notes(
        self,
        *,
        asset: Path | None = None,
        summary: str | None = None,
        decisions: str | None = None,
        actions: str | None = None,
        follow_up: str | None = None,
    ) -> None:
        document = self._ensure_document(asset)
        if document is None:
            return
        notes = document.metadata.get("meeting_notes", {})
        if not isinstance(notes, dict):
            notes = {}
        if summary is not None:
            notes["summary"] = summary.strip()
        if decisions is not None:
            notes["decisions"] = decisions.strip()
        if actions is not None:
            notes["actions"] = actions.strip()
        if follow_up is not None:
            notes["follow_up"] = follow_up.strip()
        document.metadata["meeting_notes"] = notes
        document.dirty = True
        self._autosave_document(document.asset_path)
        self._emit_update(type="meeting_notes")

    def export_meeting_markdown(self, asset: Path | None = None) -> Path:
        target = asset or self.state.selected_asset
        document = self.get_document(target)
        if target is None or document is None:
            return Path.cwd()
        notes = self.get_meeting_notes(target)
        transcript = self.get_transcript_text(target, include_timestamps=True)
        output_dir = self.resolve_output_dir(target)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = self.state.output_options.file_prefix.strip() or document.meta_file_prefix or target.stem
        markdown_path = output_dir / f"{stem}.meeting_notes.md"
        markdown = "\n\n".join(
            [
                f"# {target.stem}",
                "## Summary\n" + (notes["summary"] or "-"),
                "## Decisions\n" + (notes["decisions"] or "-"),
                "## Action Items\n" + (notes["actions"] or "-"),
                "## Follow-up\n" + (notes["follow_up"] or "-"),
                "## Transcript\n" + (transcript or "-"),
            ]
        )
        markdown_path.write_text(markdown, encoding="utf-8")
        self._emit_update(type="meeting_export", path=str(markdown_path))
        return markdown_path

    def _analyze_document(self, document: SubtitleDocument) -> tuple[list[str], str]:
        issues, confidence = analyze_document(document)
        asset = self._find_asset(document.asset_path)
        if asset is not None:
            asset.warning_count = len(issues)
            asset.review_flags = issues[:3]
            asset.confidence_summary = confidence
        return issues, confidence

    def update_segment(self, asset: Path | None, segment_id: int, field: str, value: str) -> None:
        document = self._ensure_document(asset)
        if document is None:
            return
        target = next((segment for segment in document.segments if segment.segment_id == segment_id), None)
        if target is None:
            return
        if field == "text":
            target.text = value
        else:
            number = to_float_timestamp(value) if ":" in value else float(value.strip())
            if field == "start":
                target.start = number
            elif field == "end":
                target.end = number
            else:
                return
            if target.end < target.start:
                target.start, target.end = target.end, target.start
        document.dirty = True
        document.approved = False
        document.review_status = "review_ready"
        self._reindex_segments(document)
        self._analyze_document(document)
        self._update_asset_from_document(document)
        self._autosave_document(document.asset_path)
        self._emit_update(type="segment")

    def split_segment(self, asset: Path | None, segment_id: int) -> None:
        document = self._ensure_document(asset)
        if document is None:
            return
        for index, segment in enumerate(document.segments):
            if segment.segment_id != segment_id:
                continue
            midpoint = round((segment.start + segment.end) / 2.0, 3)
            if midpoint <= segment.start or midpoint >= segment.end:
                return
            left_text, _, right_text = segment.text.partition(" ")
            first_text = left_text.strip() or segment.text.strip()
            second_text = right_text.strip() or segment.text.strip()
            document.segments[index:index + 1] = [
                SubtitleSegment(segment_id=segment.segment_id, start=segment.start, end=midpoint, text=first_text, is_generated=False),
                SubtitleSegment(segment_id=segment.segment_id + 1, start=midpoint, end=segment.end, text=second_text, is_generated=False),
            ]
            document.dirty = True
            document.approved = False
            document.review_status = "review_ready"
            self._reindex_segments(document)
            self._analyze_document(document)
            self._update_asset_from_document(document)
            self._autosave_document(document.asset_path)
            self._emit_update(type="segment_split")
            return

    def merge_segment(self, asset: Path | None, first_segment_id: int) -> None:
        document = self._ensure_document(asset)
        if document is None:
            return
        index = next((idx for idx, segment in enumerate(document.segments) if segment.segment_id == first_segment_id), -1)
        if index < 0 or index + 1 >= len(document.segments):
            return
        current = document.segments[index]
        nxt = document.segments[index + 1]
        merged = SubtitleSegment(
            segment_id=current.segment_id,
            start=min(current.start, nxt.start),
            end=max(current.end, nxt.end),
            text=f"{current.text} {nxt.text}".strip(),
            is_generated=False,
        )
        document.segments[index:index + 2] = [merged]
        document.dirty = True
        document.approved = False
        document.review_status = "review_ready"
        self._reindex_segments(document)
        self._analyze_document(document)
        self._update_asset_from_document(document)
        self._autosave_document(document.asset_path)
        self._emit_update(type="segment_merge")

    def _reindex_segments(self, document: SubtitleDocument) -> None:
        for index, segment in enumerate(document.segments):
            segment.segment_id = index

    def get_segment_at_time(self, asset: Path | None, position_ms: int) -> int | None:
        document = self.get_document(asset)
        if document is None:
            return None
        adjusted = max(0, position_ms - document.offset_ms)
        seconds = adjusted / 1000.0
        for index, segment in enumerate(document.segments):
            if segment.start <= seconds <= segment.end:
                return index
        return None

    def get_active_overlay_text(self, asset: Path | None, position_ms: int) -> str:
        document = self.get_document(asset)
        if document is None:
            return ""
        segment_index = self.get_segment_at_time(asset, position_ms)
        if segment_index is None:
            return ""
        if 0 <= segment_index < len(document.segments):
            return document.segments[segment_index].text
        return ""

    def _update_asset_from_document(self, document: SubtitleDocument) -> None:
        asset = self._find_asset(document.asset_path)
        if asset is None:
            return
        asset.approved = document.approved
        asset.status = "approved" if document.approved else document.review_status
        self._sync_counts()

    def approve_asset(self, asset: Path | None = None) -> None:
        document = self._ensure_document(asset)
        if document is None:
            return
        document.approved = True
        document.review_status = "approved"
        document.dirty = False
        self._update_asset_from_document(document)
        self._autosave_document(document.asset_path)
        self._emit_update(type="approve")

    def mark_needs_review(self, asset: Path | None = None) -> None:
        document = self._ensure_document(asset)
        if document is None:
            return
        document.approved = False
        document.review_status = "needs_retry"
        document.dirty = True
        self._update_asset_from_document(document)
        self._autosave_document(document.asset_path)
        self._emit_update(type="needs_review")

    def load_session_for_asset(self, asset_path: Path | None = None) -> SubtitleDocument | None:
        target = asset_path or self.state.selected_asset
        if target is None:
            return None
        session_path = self._session_path_for_asset(target)
        asset = self._find_asset(target)
        if asset is not None:
            asset.session_path = session_path
        if not session_path.exists():
            self.state.current_item_session = session_path
            return self._ensure_document(target)

        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
        except Exception:
            return self._ensure_document(target)

        generation_payload = payload.get("generation_options", {})
        review_payload = payload.get("review", {})
        generated_payload = payload.get("generated", {})
        document = SubtitleDocument(
            asset_path=target,
            segments=normalize_segment_payload(generated_payload.get("segments", [])) if generated_payload.get("segments") else [],
            generated_language=str(generated_payload.get("generated_language", "")),
            language_probability=float(generated_payload.get("language_probability", 0.0) or 0.0),
            generation_options=GenerationOptions(
                provider=str(generation_payload.get("provider", self.state.generation_options.provider)),
                model=str(generation_payload.get("model", self.state.generation_options.model)),
                task=str(generation_payload.get("task", self.state.generation_options.task)),
                device=str(generation_payload.get("device", self.state.generation_options.device)),
                language=str(generation_payload.get("language", self.state.generation_options.language)),
                output_formats=coerce_output_formats(generation_payload.get("output_formats", self.state.generation_options.output_formats)),
            ),
            output_paths=generated_payload.get("output_paths", {}),
            generated_formats=coerce_output_formats(generated_payload.get("generated_formats", self.state.generation_options.output_formats)),
            meta_file_prefix=str(payload.get("file_prefix", target.stem)),
            dirty=bool(generated_payload.get("dirty", False)),
            parse_error="",
            session_path=session_path,
            metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {},
            issue_messages=[str(item) for item in review_payload.get("issues", []) if str(item).strip()],
            review_status=str(review_payload.get("status", "queued")),
            approved=bool(review_payload.get("approved", False)),
            offset_ms=int(review_payload.get("offset_ms", 0) or 0),
        )
        self.state.subtitle_docs_by_path[str(target)] = document
        self.state.current_item_session = session_path
        self.state.generation_options = GenerationOptions(**asdict(document.generation_options))
        self._analyze_document(document)
        self._update_asset_from_document(document)
        if target == self.state.selected_asset:
            self.state.review_options.offset_ms = document.offset_ms
        return document

    def export_session(self, asset: Path | None = None) -> Path:
        target = asset or self.state.selected_asset
        document = self.get_document(target)
        if target is None or document is None:
            return Path.cwd()
        session_path = self._session_path_for_asset(target)
        payload = {
            "schema_version": "1.0",
            "app_id": "subtitle_qc",
            "asset_path": str(target),
            "file_prefix": document.meta_file_prefix,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "generation": {
                "status": self.state.generation_status,
                "status_tone": self.state.generation_status_tone,
                "is_processing": self.state.is_processing,
            },
            "generation_options": asdict(document.generation_options),
            "output_options": {
                "output_dir": str(self.state.output_options.output_dir) if self.state.output_options.output_dir else "",
                "file_prefix": self.state.output_options.file_prefix,
                "open_folder_after_run": self.state.output_options.open_folder_after_run,
                "export_session_json": self.state.output_options.export_session_json,
            },
            "review": {
                "status": document.review_status,
                "approved": document.approved,
                "offset_ms": document.offset_ms,
                "issues": document.issue_messages,
                "confidence_summary": self._find_asset(target).confidence_summary if self._find_asset(target) else "pending",
            },
            "generated": {
                "generated_language": document.generated_language,
                "language_probability": document.language_probability,
                "generated_formats": document.generated_formats,
                "segments": [asdict(segment) for segment in document.segments],
                "output_paths": document.output_paths,
                "dirty": document.dirty,
            },
            "metadata": document.metadata,
        }
        session_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        document.session_path = session_path
        return session_path

    def run_selected(self) -> None:
        if self.state.is_processing or self.state.selected_asset is None:
            return
        self._run_worker([self.state.selected_asset])

    def run_batch(self) -> None:
        if self.state.is_processing or not self.state.queued_assets:
            return
        self._run_worker([asset.path for asset in self.state.queued_assets])

    def retry_asset(self, asset: Path | None = None) -> None:
        target = asset or self.state.selected_asset
        if target is None or self.state.is_processing:
            return
        queue_asset = self._find_asset(target)
        if queue_asset is not None:
            queue_asset.status = "queued"
            queue_asset.retry_count += 1
        self._run_worker([target])

    def cancel_generation(self) -> None:
        if not self.state.is_processing:
            return
        self.state.cancel_requested = True
        self.state.generation_status = qt_t("subtitle_qc.status_canceling", "Cancelling...")
        self.state.generation_status_tone = "warning"
        self._emit_update(type="cancel")

    def _run_worker(self, assets: list[Path]) -> None:
        with self._thread_lock:
            if self.state.is_processing:
                return
            self.state.cancel_requested = False
            self.state.is_processing = True
            self.state.total_count = len(assets)
            self.state.completed_count = 0
            self.state.progress = 0.0
            self.state.generation_status = qt_t("subtitle_qc.status_running", "Generating subtitles...")
            self.state.generation_status_tone = "accent"
            self._thread = threading.Thread(target=self._run_assets, args=(assets,), daemon=True)
            self._thread.start()
            self._emit_update(type="run")

    def _run_assets(self, assets: list[Path]) -> None:
        errors: list[str] = []
        for index, asset_path in enumerate(assets, start=1):
            if self.state.cancel_requested:
                break
            asset = self._find_asset(asset_path)
            if asset is not None:
                asset.status = "generating"
            self.state.selected_asset = asset_path
            self.state.generation_status = qt_t(
                "subtitle_qc.status_item",
                "Processing {current}/{total}: {name}",
                current=index,
                total=len(assets),
                name=asset_path.name,
            )
            self._emit_update(type="run_progress")
            result = self._run_single_asset(asset_path)
            if not result["ok"]:
                errors.append(f"{asset_path.name}: {result['error']}")
            self.state.completed_count += 1
            self.state.progress = self.state.completed_count / max(1, self.state.total_count)
            if self.state.output_options.export_session_json:
                self._autosave_document(asset_path)
            self._emit_update(type="run_progress")

        if self.state.cancel_requested:
            self.state.generation_status = qt_t("subtitle_qc.status_cancelled", "Cancelled")
            self.state.generation_status_tone = "warning"
        elif errors:
            self.state.generation_status = qt_t("subtitle_qc.status_partial", "Completed with issues")
            self.state.generation_status_tone = "warning"
        else:
            self.state.generation_status = qt_t("subtitle_qc.status_complete", "Batch ready for review")
            self.state.generation_status_tone = "success"

        self.state.is_processing = False
        self._sync_counts()
        if not self.state.cancel_requested and not errors and self.state.output_options.open_folder_after_run and assets:
            self.reveal_output_dir(assets[0])
        self._emit_update(type="run_complete", errors=errors)

    def _run_single_asset(self, asset_path: Path) -> dict[str, Any]:
        self.state.current_item_session = self._session_path_for_asset(asset_path)
        options = self.state.generation_options
        output_dir = self.resolve_output_dir(asset_path)
        try:
            backend = backend_registry.get(options.provider)
        except ValueError as exc:
            error_message = str(exc)
            asset = self._find_asset(asset_path)
            if asset is not None:
                asset.status = "failed"
                asset.last_error = error_message
            self._sync_counts()
            return {"ok": False, "error": error_message}
        request = SubtitleGenerationRequest(
            asset_path=asset_path,
            provider=options.provider,
            model=options.model,
            task=options.task,
            device=options.device,
            language=None if options.language == "Auto" else options.language,
            output_formats=list(options.output_formats),
            output_dir=output_dir,
        )
        result = backend.generate(request)
        asset = self._find_asset(asset_path)
        if not result.success:
            error_message = result.error or "Unknown error"
            if asset is not None:
                asset.status = "failed"
                asset.last_error = error_message
            self._sync_counts()
            return {"ok": False, "error": error_message}

        document = self._ensure_document(asset_path)
        if document is None:
            return {"ok": False, "error": "Document unavailable"}
        document.segments = normalize_segment_payload(list(result.segments))
        info = result.info or {}
        document.generated_language = str(info.get("language", options.language if options.language != "Auto" else "en"))
        document.language_probability = float(info.get("language_probability", 0.0) or 0.0)
        document.generation_options = GenerationOptions(
            provider=options.provider,
            model=options.model,
            task=options.task,
            device=options.device,
            language=options.language,
            output_formats=coerce_output_formats(options.output_formats),
        )
        document.output_paths = {}
        for output_path in result.output_paths:
            fmt = Path(output_path).suffix.replace(".", "").lower()
            if fmt:
                document.output_paths.setdefault(fmt, []).append(str(output_path))
        document.generated_formats = coerce_output_formats(options.output_formats)
        document.review_status = "review_ready"
        document.approved = False
        document.dirty = False
        document.offset_ms = self.state.review_options.offset_ms
        document.metadata = {
            "provider": options.provider,
            "task": options.task,
            "model": options.model,
            "device": options.device,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._analyze_document(document)
        self.state.last_completed_asset = asset_path
        if asset is not None:
            asset.status = "review_ready"
            asset.last_error = ""
        self._update_asset_from_document(document)
        return {"ok": True}
