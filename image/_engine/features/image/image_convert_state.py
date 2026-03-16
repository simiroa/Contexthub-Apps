from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InputAsset:
    path: Path
    kind: str


@dataclass
class OutputOptions:
    output_dir: Path = Path.home() / "Pictures" / "ContextHub_Exports"
    file_prefix: str = "convert"
    open_folder_after_run: bool = True
    export_session_json: bool = True


@dataclass
class ImageConvertState:
    workflow_name: str = "Batch Conversion"
    workflow_description: str = "Convert images to various formats with optional long-edge resizing."
    preview_path: Path | None = None
    input_assets: list[InputAsset] = field(default_factory=list)
    parameter_values: dict[str, object] = field(default_factory=dict)
    output_options: OutputOptions = field(default_factory=OutputOptions)
