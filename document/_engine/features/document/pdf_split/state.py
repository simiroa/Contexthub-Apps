"""PDF split application state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class PdfSplitState:
    files: List[Path] = field(default_factory=list)
    mode: str = "pdf"  # "pdf", "png", "jpg"
    dpi: int = 300
    is_processing: bool = False
    is_cancelled: bool = False
    status_text: str = ""
    detail_text: str = ""
    progress: float = 0.0
    error: str = ""
