from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Any

@dataclass
class InputAsset:
    path: Path
    kind: str = "file"

@dataclass
class OutputOptions:
    output_dir: Optional[Path] = None
    file_prefix: str = "processed"
    open_folder_after_run: bool = True
    export_session_json: bool = False

@dataclass
class __APP_CLASS_NAME__State:
    input_assets: List[InputAsset] = field(default_factory=list)
    parameter_values: dict = field(default_factory=dict)
    output_options: OutputOptions = field(default_factory=OutputOptions)
    
    preview_path: Optional[Path] = None
    workflow_name: str = "Default"
