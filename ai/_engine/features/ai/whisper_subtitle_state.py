from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SUPPORTED_MEDIA_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".flac", ".ogg"}


@dataclass
class InputAsset:
    path: Path
    kind: str


@dataclass
class OutputOptions:
    output_dir: Path | None = None
    file_prefix: str = "subtitle"
    open_folder_after_run: bool = True
    export_session_json: bool = True


@dataclass
class SubtitleSegment:
    segment_id: int
    start: float
    end: float
    text: str
    is_generated: bool = True


@dataclass
class GenerationOptions:
    model: str = "small"
    task: str = "transcribe"
    device: str = "cuda"
    language: str = "Auto"
    output_formats: list[str] = field(default_factory=lambda: ["srt", "vtt"])


@dataclass
class SubtitleDocument:
    asset_path: Path
    segments: list[SubtitleSegment] = field(default_factory=list)
    generated_language: str = ""
    language_probability: float | None = None
    generation_options: GenerationOptions = field(default_factory=GenerationOptions)
    output_paths: dict[str, list[str]] = field(default_factory=dict)
    generated_formats: list[str] = field(default_factory=lambda: ["srt", "vtt"])
    generated_payload: list[dict[str, Any]] = field(default_factory=list)
    meta_file_prefix: str = "subtitle"
    dirty: bool = False
    parse_error: str = ""
    session_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WhisperSubtitleState:
    queued_assets: list[InputAsset] = field(default_factory=list)
    selected_asset: Path | None = None
    generation_status: str = "Ready"
    generation_status_tone: str = "ready"
    generation_summary: str = ""
    current_item_session: Path | None = None
    subtitle_docs_by_path: dict[str, SubtitleDocument] = field(default_factory=dict)
    dirty_flag: bool = False
    generation_options: GenerationOptions = field(default_factory=GenerationOptions)
    output_options: OutputOptions = field(default_factory=OutputOptions)
    is_processing: bool = False
    total_count: int = 0
    completed_count: int = 0
    progress: float = 0.0
    cancel_requested: bool = False
