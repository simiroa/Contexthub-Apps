from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SUPPORTED_MEDIA_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".flac", ".ogg"}
ASSET_STATUSES = ("queued", "generating", "review_ready", "approved", "needs_retry", "failed")


@dataclass
class InputAsset:
    asset_id: str
    path: Path
    kind: str
    status: str = "queued"
    confidence_summary: str = "pending"
    session_path: Path | None = None
    review_flags: list[str] = field(default_factory=list)
    warning_count: int = 0
    approved: bool = False
    last_error: str = ""
    retry_count: int = 0


@dataclass
class OutputOptions:
    output_dir: Path | None = None
    file_prefix: str = "subtitle"
    open_folder_after_run: bool = True
    export_session_json: bool = True


@dataclass
class ReviewOptions:
    overlay_enabled: bool = True
    overlay_font_percent: int = 100
    offset_ms: int = 0
    playback_rate: float = 1.0
    auto_advance_review: bool = True


@dataclass
class GenerationOptions:
    provider: str = "whisper"
    model: str = "small"
    task: str = "transcribe"
    device: str = "cuda"
    language: str = "Auto"
    output_formats: list[str] = field(default_factory=lambda: ["srt", "vtt", "txt"])


@dataclass
class SubtitleSegment:
    segment_id: int
    start: float
    end: float
    text: str
    is_generated: bool = True
    review_flags: list[str] = field(default_factory=list)


@dataclass
class SubtitleDocument:
    asset_path: Path
    segments: list[SubtitleSegment] = field(default_factory=list)
    generated_language: str = ""
    language_probability: float | None = None
    generation_options: GenerationOptions = field(default_factory=GenerationOptions)
    output_paths: dict[str, list[str]] = field(default_factory=dict)
    generated_formats: list[str] = field(default_factory=lambda: ["srt", "vtt", "txt"])
    meta_file_prefix: str = "subtitle"
    dirty: bool = False
    parse_error: str = ""
    session_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    issue_messages: list[str] = field(default_factory=list)
    review_status: str = "queued"
    approved: bool = False
    offset_ms: int = 0


@dataclass
class SubtitleQcState:
    queued_assets: list[InputAsset] = field(default_factory=list)
    selected_asset: Path | None = None
    generation_status: str = "Ready"
    generation_status_tone: str = "ready"
    current_item_session: Path | None = None
    subtitle_docs_by_path: dict[str, SubtitleDocument] = field(default_factory=dict)
    dirty_flag: bool = False
    generation_options: GenerationOptions = field(default_factory=GenerationOptions)
    output_options: OutputOptions = field(default_factory=OutputOptions)
    review_options: ReviewOptions = field(default_factory=ReviewOptions)
    is_processing: bool = False
    total_count: int = 0
    completed_count: int = 0
    approved_count: int = 0
    failed_count: int = 0
    progress: float = 0.0
    cancel_requested: bool = False
    last_completed_asset: Path | None = None
