"""Document conversion application state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class DocConvertState:
    files: List[Path] = field(default_factory=list)
    target_format: str = ""
    available_formats: List[str] = field(default_factory=list)
    dpi: int = 300
    use_subfolder: bool = True
    is_processing: bool = False
    status_text: str = ""
    detail_text: str = ""
    progress: float = 0.0
    errors: List[str] = field(default_factory=list)
