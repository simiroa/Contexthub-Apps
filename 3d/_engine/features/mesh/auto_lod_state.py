from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AutoLodState:
    input_path: Path | None = None
    generated_paths: list[Path] | None = None
    selected_view: str = "source"
    selected_lod_index: int = 0

    lod_ratio: float = 0.5
    lod_count: int = 3
    preserve_uv: bool = True
    preserve_normal: bool = True
    preserve_boundary: bool = True

    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    error_message: str | None = None
