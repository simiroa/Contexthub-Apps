"""PDF merge application state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class OutputOptions:
    output_dir: Path = Path.home() / "Documents" / "ContextHub_Exports"
    file_prefix: str = "merged"
    open_folder_after_run: bool = True
    export_session_json: bool = False


@dataclass
class PdfMergeState:
    files: List[Path] = field(default_factory=list)
    selected_index: int = -1
    output_options: OutputOptions = field(default_factory=OutputOptions)
    last_output_path: Optional[Path] = None
    is_processing: bool = False
    status_text: str = "Ready"
    detail_text: str = ""
    progress: float = 0.0
    error: str = ""
