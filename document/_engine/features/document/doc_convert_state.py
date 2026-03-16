from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class InputAsset:
    path: Path
    kind: str


@dataclass
class OutputOptions:
    output_dir: Path = Path.home() / "Documents" / "ContextHub_Exports"
    file_prefix: str = "doc_convert"
    open_folder_after_run: bool = True
    export_session_json: bool = True
    use_subfolder: bool = True


@dataclass
class DocConvertState:
    workflow_name: str = "Default"
    workflow_description: str = "Document conversion presets."
    preview_path: Path | None = None
    input_assets: list[InputAsset] = field(default_factory=list)
    parameter_values: dict[str, object] = field(default_factory=dict)
    output_options: OutputOptions = field(default_factory=OutputOptions)
    
    # Run state
    is_processing: bool = False
    status_text: str = ""
    detail_text: str = ""
    progress: float = 0.0
    errors: list[str] = field(default_factory=list)
    last_converted: Optional[Path] = None
