from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from contexthub.ui.qt.shell import qt_t

from features.ai.whisper_subtitle_state import (
    SUPPORTED_MEDIA_EXTS,
    GenerationOptions,
    InputAsset,
    OutputOptions,
    SubtitleDocument,
    SubtitleSegment,
    WhisperSubtitleState,
)


SUPPORTED_FORMATS = {"srt", "vtt", "txt", "json"}
_TIMESTAMP_RE = re.compile(r"(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d+)(?:[.,](?P<ms>\d{1,3}))?")


def _to_float_timestamp(value: str) -> float:
    value = value.strip()
    if not value:
        raise ValueError(qt_t("whisper_subtitle.timestamp_empty", "Empty timestamp"))

    match = _TIMESTAMP_RE.match(value)
    if not match:
        raise ValueError(qt_t("whisper_subtitle.timestamp_invalid", "Invalid timestamp: {value}", value=value))
    parts = match.groupdict()
    seconds = float(parts["s"])
    milliseconds = parts.get("ms") or "0"
    if len(milliseconds) == 1:
        milliseconds = f"{milliseconds}00"
    elif len(milliseconds) == 2:
        milliseconds = f"{milliseconds}0"
    return int(parts["h"]) * 3600 + int(parts["m"]) * 60 + seconds + int(milliseconds[:3]) / 1000.0


def _parse_timestamp_line(line: str) -> tuple[float, float]:
    if "-->" not in line:
        raise ValueError(qt_t("whisper_subtitle.timestamp_line_required", "Expected timestamp line"))
    left, right = line.split("-->", 1)
    start_token = left.strip().split()[0]
    end_token = right.strip().split()[0]
    return _to_float_timestamp(start_token), _to_float_timestamp(end_token)


def _parse_raw_segments(text: str) -> list[dict[str, Any]]:
    rows = [line.rstrip() for line in text.splitlines()]
    index = 0
    parsed: list[dict[str, Any]] = []
    while index < len(rows):
        line = rows[index].strip()
        if not line:
            index += 1
            continue

        if line.lower() == "webvtt":
            index += 1
            continue

        if line.isdigit():
            index += 1
            if index >= len(rows):
                break
            if "-->" not in rows[index]:
                raise ValueError(qt_t("whisper_subtitle.timestamp_required", "Timestamp line required"))
            timestamp_line = rows[index]
            index += 1
        else:
            timestamp_line = line
            if "-->" not in timestamp_line:
                raise ValueError(qt_t("whisper_subtitle.timestamp_required", "Timestamp line required"))

        start, end = _parse_timestamp_line(timestamp_line)
        content: list[str] = []
        while index < len(rows) and rows[index].strip():
            content.append(rows[index].strip())
            index += 1
        parsed.append({"start": start, "end": end, "text": "\n".join(content).strip()})
        while index < len(rows) and not rows[index].strip():
            index += 1

    return parsed


def _parse_srt_text(text: str) -> list[dict[str, Any]]:
    return _parse_raw_segments(text)


def _parse_vtt_text(text: str) -> list[dict[str, Any]]:
    return _parse_raw_segments(text)


def _coerce_output_formats(formats: list[str] | None) -> list[str]:
    if not formats:
        return ["srt", "vtt"]
    cleaned = [fmt.strip().lower() for fmt in formats if isinstance(fmt, str)]
    cleaned = [fmt for fmt in cleaned if fmt in SUPPORTED_FORMATS]
    return cleaned or ["srt", "vtt"]


def _format_timestamp(seconds: float, fmt: str = "srt") -> str:
    total = max(0.0, float(seconds))
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    sec = total % 60
    milliseconds = int((sec - int(sec)) * 1000)
    if fmt == "vtt":
        return f"{hours:02d}:{minutes:02d}:{int(sec):02d}.{milliseconds:03d}"
    return f"{hours:02d}:{minutes:02d}:{int(sec):02d},{milliseconds:03d}"


def _segments_to_export_payload(document: SubtitleDocument, fmt: str) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for segment in document.segments:
        rows.append(
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "id": segment.segment_id,
                "fmt": fmt,
            }
        )
    return rows


def _normalize_segment_payload(raw_segments: list[dict[str, Any]]) -> list[SubtitleSegment]:
    normalized: list[SubtitleSegment] = []
    for index, entry in enumerate(raw_segments):
        text = str(entry.get("text", "")).strip()
        if not text:
            continue
        start = float(entry.get("start", 0.0))
        end = float(entry.get("end", 0.0))
        if end < start:
            start, end = end, start
        normalized.append(SubtitleSegment(segment_id=index, start=start, end=end, text=text, is_generated=False))
    if not normalized:
        raise ValueError(qt_t("whisper_subtitle.no_segments", "No valid subtitle segments"))
    return normalized


class WhisperSubtitleService:
    def __init__(self, on_update: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.state = WhisperSubtitleState()
        self._on_update = on_update
        self._thread: threading.Thread | None = None
        self._thread_lock = threading.Lock()

    def _emit_update(self, **payload: Any) -> None:
        if not self._on_update:
            return
        payload.setdefault("generation_status", self.state.generation_status)
        payload.setdefault("is_processing", self.state.is_processing)
        payload.setdefault("generation_status_tone", self.state.generation_status_tone)
        payload.setdefault("dirty_flag", self.state.dirty_flag)
        payload.setdefault("progress", self.state.progress)
        payload.setdefault("queue_count", len(self.state.queued_assets))
        self._on_update(payload)

    def _session_path_for_asset(self, path: Path) -> Path:
        return path.with_name(f"{path.stem}.subtitle_session.json")

    def add_inputs(self, paths: list[str]) -> None:
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
                self.state.queued_assets.append(InputAsset(path=candidate, kind=kind))

        if self.state.selected_asset is None and self.state.queued_assets:
            self.state.selected_asset = self.state.queued_assets[0].path
            self.load_session_for_asset(self.state.selected_asset)

        self.state.generation_status = qt_t("whisper_subtitle.ready", "Ready")
        self._emit_update(type="queue")

    def remove(self, index: int) -> None:
        self.remove_input_at(index)

    def remove_input_at(self, index: int) -> None:
        if not (0 <= index < len(self.state.queued_assets)):
            return
        removed = self.state.queued_assets.pop(index)
        self.state.subtitle_docs_by_path.pop(str(removed.path), None)
        if self.state.selected_asset == removed.path:
            self.state.selected_asset = self.state.queued_assets[0].path if self.state.queued_assets else None
            self.state.current_item_session = self._session_path_for_asset(self.state.selected_asset) if self.state.selected_asset else None

        if self.state.selected_asset is None:
            self.state.current_item_session = None
        self.state.dirty_flag = any(item.dirty for item in self.state.subtitle_docs_by_path.values())
        self._emit_update(type="queue")

    def clear_inputs(self) -> None:
        self.state.queued_assets.clear()
        self.state.subtitle_docs_by_path.clear()
        self.state.selected_asset = None
        self.state.current_item_session = None
        self.state.dirty_flag = False
        self.state.total_count = 0
        self.state.completed_count = 0
        self.state.progress = 0.0
        self.state.is_processing = False
        self.state.cancel_requested = False
        self.state.generation_status = qt_t("whisper_subtitle.ready", "Ready")
        self.state.generation_status_tone = "ready"
        self._emit_update(type="queue")

    def set_selected_asset(self, path: str | Path | None) -> None:
        selected = Path(path) if path else None
        if selected is None or selected not in [asset.path for asset in self.state.queued_assets]:
            self.state.selected_asset = None
            self.state.current_item_session = None
            self._emit_update(type="selection")
            return

        self.state.selected_asset = selected
        self.state.current_item_session = self._session_path_for_asset(selected)
        if self._ensure_document(selected) is None:
            self.load_session_for_asset(selected)
        self._emit_update(type="selection")

    def get_selected_items(self) -> list[tuple[str, str]]:
        return [(asset.path.name, str(asset.path)) for asset in self.state.queued_assets]

    def get_selected_asset(self) -> InputAsset | None:
        if self.state.selected_asset is None:
            return None
        for asset in self.state.queued_assets:
            if asset.path == self.state.selected_asset:
                return asset
        return None

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
            generated_formats=_coerce_output_formats(self.state.generation_options.output_formats),
        )
        self.state.subtitle_docs_by_path[str(target)] = document
        return document

    def get_documents(self, asset: Path | None = None) -> SubtitleDocument | None:
        target = asset or self.state.selected_asset
        if target is None:
            return None
        return self.state.subtitle_docs_by_path.get(str(target))

    def update_generation_options(
        self,
        *,
        model: str | None = None,
        task: str | None = None,
        device: str | None = None,
        language: str | None = None,
        output_formats: list[str] | None = None,
    ) -> None:
        options = self.state.generation_options
        if model is not None:
            options.model = model
        if task is not None:
            options.task = task
        if device is not None:
            options.device = device
        if language is not None:
            options.language = language
        if output_formats is not None:
            options.output_formats = _coerce_output_formats(output_formats)
        self._emit_update(type="options")

    def update_output_options(self, output_dir: str, file_prefix: str, open_folder_after_run: bool, export_session_json: bool) -> None:
        options = self.state.output_options
        options.output_dir = Path(output_dir) if output_dir.strip() else None
        options.file_prefix = file_prefix.strip() or "subtitle"
        options.open_folder_after_run = bool(open_folder_after_run)
        options.export_session_json = bool(export_session_json)
        self._emit_update(type="output_options")

    def resolve_output_dir(self, asset: Path | None = None) -> Path:
        if self.state.output_options.output_dir:
            return self.state.output_options.output_dir
        if asset:
            return asset.parent
        if self.state.selected_asset:
            return self.state.selected_asset.parent
        return Path.cwd()

    def reveal_output_dir(self, asset: Path | None = None) -> None:
        output_dir = self.resolve_output_dir(asset)
        output_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(output_dir)

    def _write_segments_to_file(
        self,
        asset: Path,
        document: SubtitleDocument,
        fmt: str,
        output_dir: Path,
        output_name: str | None = None,
    ) -> str:
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = output_name or document.meta_file_prefix or asset.stem
        if fmt == "txt":
            target = output_dir / f"{stem}.txt"
        elif fmt == "json":
            target = output_dir / f"{stem}.json"
        else:
            target = output_dir / f"{stem}.{document.generated_language or 'en'}.{fmt}"

        with open(target, "w", encoding="utf-8") as stream:
            if fmt == "srt":
                for index, segment in enumerate(document.segments, start=1):
                    stream.write(f"{index}\n")
                    stream.write(f"{_format_timestamp(segment.start, 'srt')} --> {_format_timestamp(segment.end, 'srt')}\n")
                    stream.write(f"{segment.text}\n\n")
            elif fmt == "vtt":
                stream.write("WEBVTT\n\n")
                for segment in document.segments:
                    stream.write(f"{_format_timestamp(segment.start, 'vtt')} --> {_format_timestamp(segment.end, 'vtt')}\n")
                    stream.write(f"{segment.text}\n\n")
            elif fmt == "txt":
                for segment in document.segments:
                    stream.write(f"{segment.text}\n")
            elif fmt == "json":
                payload = [
                    {"start": segment.start, "end": segment.end, "text": segment.text, "segment_id": segment.segment_id}
                    for segment in document.segments
                ]
                json.dump(payload, stream, ensure_ascii=False, indent=2)

        return str(target)

    def save_subtitles(
        self,
        asset: Path,
        formats: list[str] | None = None,
        output_dir_override: Path | str | None = None,
    ) -> dict[str, list[str]]:
        document = self._ensure_document(asset)
        if document is None:
            return {}

        output_dir = Path(output_dir_override) if output_dir_override else self.resolve_output_dir(asset)
        chosen_formats = _coerce_output_formats(formats or document.generated_formats)
        output_paths: dict[str, list[str]] = {}
        output_name = document.meta_file_prefix or asset.stem

        for fmt in chosen_formats:
            path = self._write_segments_to_file(asset, document, fmt, output_dir, output_name=output_name)
            output_paths.setdefault(fmt, []).append(path)

        document.output_paths = output_paths
        document.generated_formats = chosen_formats
        document.dirty = False
        self.state.dirty_flag = any(doc.dirty for doc in self.state.subtitle_docs_by_path.values())
        self._emit_update(type="document", output_paths=output_paths)
        return output_paths

    def get_segment_at_time(self, asset: Path | None, ms: int) -> int | None:
        document = self._ensure_document(asset)
        if document is None:
            return None
        current = float(ms) / 1000.0
        for row, segment in enumerate(document.segments):
            if segment.start <= current <= segment.end:
                return row
        return None

    def update_segment(self, asset: Path | None, seg_id: int, field: str, value: str) -> None:
        document = self._ensure_document(asset)
        if document is None:
            return

        target = None
        for segment in document.segments:
            if segment.segment_id == seg_id:
                target = segment
                break
        if target is None:
            return

        if field == "text":
            target.text = value
        else:
            try:
                number = float(value.strip())
            except ValueError as exc:
                document.parse_error = str(exc)
                self._emit_update(type="document", parse_error=document.parse_error)
                return

            if field == "start":
                target.start = number
            elif field == "end":
                target.end = number
            else:
                return

            if target.end < target.start:
                target.start, target.end = target.end, target.start

        target.is_generated = False
        document.dirty = True
        document.parse_error = ""
        self.state.dirty_flag = True
        self._emit_update(type="segment")

    def apply_text_edit(self, asset: Path | None, fmt: str, text: str) -> tuple[bool, str]:
        document = self._ensure_document(asset)
        if document is None:
            return False, qt_t("whisper_subtitle.no_document", "No subtitle document")

        parser = _parse_srt_text if fmt == "srt" else _parse_vtt_text
        try:
            parsed_segments = parser(text)
            normalized = _normalize_segment_payload(parsed_segments)
        except Exception as exc:
            document.parse_error = str(exc)
            self._emit_update(type="document", parse_error=document.parse_error)
            return False, document.parse_error

        document.segments = normalized
        document.parse_error = ""
        document.dirty = True
        self.state.dirty_flag = True
        self._emit_update(type="document", parse_error="")
        return True, qt_t("whisper_subtitle.applied", "Applied")

    def load_session_for_asset(self, asset_path: Path | None = None) -> SubtitleDocument | None:
        target = asset_path or self.state.selected_asset
        if target is None:
            return None

        session_path = self._session_path_for_asset(target)
        if not session_path.exists():
            self.state.current_item_session = session_path
            self.state.subtitle_docs_by_path.pop(str(target), None)
            self._ensure_document(target)
            return self.state.subtitle_docs_by_path.get(str(target))

        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

        generated = payload.get("generated", {})
        if not isinstance(generated, dict):
            generated = {}
        options_payload = generated.get("generation_options", {})
        if not isinstance(options_payload, dict):
            options_payload = {}
        options = self.state.generation_options
        if options_payload:
            options = GenerationOptions(
                model=str(options_payload.get("model", options.model)),
                task=str(options_payload.get("task", options.task)),
                device=str(options_payload.get("device", options.device)),
                language=str(options_payload.get("language", options.language)),
                output_formats=_coerce_output_formats(options_payload.get("output_formats", options.output_formats)),
            )
            self.state.generation_options = options

        document_segments = []
        for index, raw_segment in enumerate(generated.get("segments", [])):
            if not isinstance(raw_segment, dict):
                continue
            text = str(raw_segment.get("text", "")).strip()
            if not text:
                continue
            segment_id = raw_segment.get("segment_id", index)
            document_segments.append(
                SubtitleSegment(
                    segment_id=int(segment_id),
                    start=float(raw_segment.get("start", 0.0)),
                    end=float(raw_segment.get("end", 0.0)),
                    text=text,
                    is_generated=bool(raw_segment.get("is_generated", False)),
                )
            )

        segments = []
        if document_segments:
            segments = document_segments
        elif generated.get("raw_segments") and isinstance(generated.get("raw_segments"), list):
            try:
                segments = _normalize_segment_payload(generated.get("raw_segments"))  # type: ignore[arg-type]
            except Exception:
                segments = []

        document = SubtitleDocument(
            asset_path=target,
            segments=segments,
            generated_language=str(generated.get("generated_language", "")),
            language_probability=float(generated.get("language_probability", 0.0) or 0.0),
            generation_options=options,
            output_paths=generated.get("output_paths", {}),
            dirty=bool(generated.get("dirty", False)),
            parse_error="",
            metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {},
            session_path=session_path,
            generated_formats=_coerce_output_formats(generated.get("generated_formats", [])),
            meta_file_prefix=str(payload.get("file_prefix", target.stem)),
        )

        self.state.subtitle_docs_by_path[str(target)] = document
        self.state.current_item_session = session_path
        self.state.dirty_flag = any(item.dirty for item in self.state.subtitle_docs_by_path.values())
        return document

    def export_session(self, asset: Path | None = None) -> Path:
        target = asset or self.state.selected_asset
        if target is None:
            return Path.cwd()

        document = self._ensure_document(target)
        if document is None:
            return Path.cwd()

        payload = {
            "schema_version": "1.1",
            "app_id": "whisper_subtitle",
            "asset_path": str(target),
            "file_prefix": document.meta_file_prefix,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "generation": {
                "status": self.state.generation_status,
                "status_tone": self.state.generation_status_tone,
                "is_processing": self.state.is_processing,
            },
            "options": asdict(self.state.output_options),
            "generation_options": asdict(document.generation_options),
            "generated": {
                "generated_language": document.generated_language,
                "language_probability": document.language_probability,
                "generated_formats": document.generated_formats,
                "segments": [asdict(segment) for segment in document.segments],
                "output_paths": document.output_paths,
                "dirty": document.dirty,
                "raw_segments": _segments_to_export_payload(document, "raw"),
            },
            "metadata": document.metadata,
        }

        session_path = self._session_path_for_asset(target)
        payload["file_path"] = str(session_path)
        session_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        document.session_path = session_path
        return session_path

    def run_selected(self) -> None:
        if self.state.is_processing:
            return
        selected = self.state.selected_asset
        if selected is None:
            return
        self._run_worker([selected])

    def run_batch(self) -> None:
        if self.state.is_processing or not self.state.queued_assets:
            return
        self._run_worker([asset.path for asset in self.state.queued_assets])

    def cancel_generation(self) -> None:
        if not self.state.is_processing:
            return
        self.state.cancel_requested = True
        self.state.generation_status = qt_t("whisper_subtitle.status_canceling", "Cancelling...")
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
            self.state.dirty_flag = False
            self.state.generation_status = qt_t("whisper_subtitle.status_running", "Generating...")
            self.state.generation_status_tone = "running"
            self._emit_update(type="run")

            self._thread = threading.Thread(target=self._run_assets, args=(assets,), daemon=True)
            self._thread.start()

    def _run_assets(self, assets: list[Path]) -> None:
        errors: list[str] = []
        for index, asset in enumerate(assets, start=1):
            if self.state.cancel_requested:
                break

            self.state.generation_status = qt_t(
                "whisper_subtitle.status_item",
                "Processing {current}/{total}: {name}",
                current=index,
                total=len(assets),
                name=asset.name,
            )
            self._emit_update(type="run_progress")

            result = self._run_single_asset(asset)
            if not result["ok"]:
                errors.append(f"{asset.name}: {result['error']}")

            self.state.completed_count += 1
            self.state.progress = self.state.completed_count / max(1, self.state.total_count)
            if self.state.output_options.export_session_json:
                try:
                    self.export_session(asset)
                except Exception:
                    pass

            self._emit_update(type="run_progress", progress=self.state.progress)

        if self.state.cancel_requested:
            self.state.generation_status = qt_t("whisper_subtitle.status_cancelled", "Cancelled")
            self.state.generation_status_tone = "warning"
        elif errors:
            self.state.generation_status = qt_t("whisper_subtitle.status_partial", "Completed with errors: {count}", count=len(errors))
            self.state.generation_status_tone = "error"
        else:
            self.state.generation_status = qt_t("whisper_subtitle.status_complete", "Generation complete")
            self.state.generation_status_tone = "success"

        self.state.is_processing = False
        if not self.state.cancel_requested and not errors and self.state.output_options.open_folder_after_run and assets:
            self.reveal_output_dir(assets[0])

        self._emit_update(type="run_complete", status=self.state.generation_status, errors=errors)

    def _run_single_asset(self, asset: Path) -> dict[str, Any]:
        self.state.current_item_session = self._session_path_for_asset(asset)
        options = self.state.generation_options
        output_dir = str(self.resolve_output_dir(asset))
        # `subtitle_gen` pulls in heavy ML dependencies; defer that import until the user starts generation.
        from features.ai.standalone.subtitle_gen import generate_subtitles

        result = generate_subtitles(
            str(asset),
            model_size=options.model,
            device=options.device,
            task=options.task,
            language=None if options.language == "Auto" else options.language,
            output_formats=options.output_formats,
            output_dir=output_dir,
            return_result=True,
        )

        if not isinstance(result, dict):
            return {"ok": False, "error": qt_t("whisper_subtitle.error_result", "Unknown generation result")}

        if not result.get("success"):
            return {"ok": False, "error": str(result.get("error", qt_t("whisper_subtitle.error_unknown", "Unknown error")))}

        document = self._ensure_document(asset)
        if document is None:
            return {"ok": False, "error": qt_t("whisper_subtitle.no_document", "No subtitle document")}

        document.segments = _normalize_segment_payload(list(result.get("segments", [])))
        info = result.get("info") or {}
        document.generated_language = str(
            info.get(
                "language",
                options.language if options.language != "Auto" else "en",
            )
        )
        document.language_probability = float(info.get("language_probability", 0.0) or 0.0)
        document.generation_options = GenerationOptions(
            model=options.model,
            task=options.task,
            device=options.device,
            language=options.language,
            output_formats=_coerce_output_formats(options.output_formats),
        )
        document.output_paths = {}
        for output_path in result.get("output_paths", []):
            fmt = Path(output_path).suffix.replace(".", "").lower()
            if fmt:
                document.output_paths.setdefault(fmt, []).append(str(output_path))
        document.generated_formats = _coerce_output_formats(options.output_formats)
        document.generated_payload = _segments_to_export_payload(document, "generated")
        document.dirty = False
        document.parse_error = ""
        document.metadata = {
            "task": options.task,
            "model": options.model,
            "device": options.device,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "output_path_count": sum(len(paths) for paths in document.output_paths.values()),
        }
        self.state.subtitle_docs_by_path[str(asset)] = document
        if self.state.output_options.export_session_json:
            try:
                self.export_session(asset)
            except Exception:
                pass
        return {"ok": True}
