from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SubtitleGenerationRequest:
    asset_path: Path
    provider: str
    model: str
    task: str
    device: str
    language: str | None
    output_formats: list[str]
    output_dir: Path


@dataclass(frozen=True)
class SubtitleGenerationResult:
    success: bool
    segments: list[dict[str, float | str]] = field(default_factory=list)
    info: dict[str, object] = field(default_factory=dict)
    output_paths: list[str] = field(default_factory=list)
    error: str = ""


class SubtitleGenerationBackend(Protocol):
    provider_id: str

    def generate(self, request: SubtitleGenerationRequest) -> SubtitleGenerationResult:
        ...
