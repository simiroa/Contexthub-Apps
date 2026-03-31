from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from features.audio.audio_toolbox_tasks import (
    COMPRESS_LEVELS,
    COMPRESS_OUTPUT_FORMATS,
    CONVERT_OUTPUT_FORMATS,
    CONVERT_QUALITIES,
    ENHANCE_OUTPUT_FORMATS,
    ENHANCE_PROFILES,
    SEPARATOR_MODELS,
    SEPARATOR_OUTPUT_FORMATS,
    SEPARATOR_STEM_MODES,
    TASK_COMPRESS_AUDIO,
    TASK_CONVERT_AUDIO,
    TASK_ENHANCE_AUDIO,
    TASK_EXTRACT_ALL_AUDIO,
    TASK_EXTRACT_BGM,
    TASK_EXTRACT_VOICE,
    TASK_LABELS,
    TASK_NORMALIZE_VOLUME,
)

AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"
}


@dataclass
class AudioToolboxState:
    files: list[Path] = field(default_factory=list)
    selected_index: int = -1
    task_type: str = TASK_EXTRACT_VOICE

    output_mode: str = "source_folder"
    custom_output_dir: Optional[Path] = None
    export_format: str = ""

    model: str = SEPARATOR_MODELS[0]
    separator_output_format: str = "wav"
    stem_mode: str = "Selected stem only"
    chunk_duration: int = 0

    target_loudness: float = -16.0
    true_peak: float = -1.5
    loudness_range: float = 11.0

    convert_output_format: str = "MP3"
    convert_quality: str = "High"
    copy_metadata: bool = True
    delete_original: bool = False

    compress_output_format: str = "M4A"
    compress_level: str = "Balanced"

    enhance_profile: str = ENHANCE_PROFILES[0]
    enhance_output_format: str = "WAV"

    trim_enabled: bool = False
    trim_start: str = ""
    trim_end: str = ""

    is_processing: bool = False
    progress_value: float = 0.0
    status_text: str = "Ready"
    detail_text: str = ""
    completed_count: int = 0
    total_count: int = 0
    error_message: Optional[str] = None
    last_output_path: Optional[Path] = None

    ffmpeg_available: bool = False
    audio_separator_available: bool = False
    demucs_available: bool = False
    active_backend: str = ""


def pick_supported_audio(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        path = Path(target).resolve()
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append(path)
    return files
