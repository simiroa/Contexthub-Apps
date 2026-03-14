"""PDF merge application state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class PdfMergeState:
    files: List[Path] = field(default_factory=list)
    is_processing: bool = False
    status_text: str = ""
    detail_text: str = ""
    progress: float = 0.0
    error: str = ""
