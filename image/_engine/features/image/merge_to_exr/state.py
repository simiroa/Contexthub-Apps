from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ChannelConfig:
    source_file: Optional[str] = None
    target_name: str = ""
    mode: str = "RGB"
    depth: str = "HALF"
    invert: bool = False
    linear: bool = False
    enabled: bool = True


@dataclass
class OutputOptions:
    output_dir: Path = Path.home() / "Pictures" / "ContextHub_Exports"
    file_prefix: str = "MultiLayer_Output"
    open_folder_after_run: bool = True
    export_session_json: bool = False


@dataclass
class ExrMergeState:
    files: List[Path] = field(default_factory=list)
    channels: List[ChannelConfig] = field(default_factory=list)
    selected_index: int = -1
    common_prefix: str = ""
    output_options: OutputOptions = field(default_factory=OutputOptions)
    is_exporting: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    detail_text: str = "Add source images to build EXR layers."
    output_path: Optional[Path] = None
    error_text: str = ""
