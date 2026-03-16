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
    file_prefix: str = ""
    open_folder_after_run: bool = True
    export_session_json: bool = False


@dataclass
class BackgroundRemovalState:
    model: str = "birefnet"
    postprocess: str = "none"
    transparent: bool = True
    preview_path: Path | None = None
    input_assets: list[InputAsset] = field(default_factory=list)
    parameter_values: dict[str, object] = field(default_factory=dict)
    output_options: OutputOptions = field(default_factory=OutputOptions)
