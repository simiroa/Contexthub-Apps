from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InputAsset:
    path: Path
    kind: str


@dataclass
class OutputOptions:
    output_dir: Path | None = None
    file_prefix: str = "resized"
    open_folder_after_run: bool = True
    export_session_json: bool = True


@dataclass
class ImageResizerState:
    workflow_name: str = "Image Resize"
    workflow_description: str = "Versatile image scaling utility with P02, Ratio, and Custom modes."
    preview_path: Path | None = None
    input_assets: list[InputAsset] = field(default_factory=list)
    parameter_values: dict[str, object] = field(default_factory=dict)
    output_options: OutputOptions = field(default_factory=OutputOptions)
