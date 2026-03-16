from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class InputAsset:
    path: Path
    kind: str = "image"


@dataclass
class OutputOptions:
    output_dir: Path
    file_prefix: str = "creative_studio"
    open_folder_after_run: bool = True
    export_session_json: bool = True


@dataclass
class CreativeStudioAdvancedState:
    workflow_name: str = ""
    workflow_description: str = ""
    status_text: str = "Checking ComfyUI runtime..."
    status_level: str = "info"
    preview_path: Path | None = None
    input_assets: list[InputAsset] = field(default_factory=list)
    parameter_values: dict[str, Any] = field(default_factory=dict)
    output_options: OutputOptions = field(
        default_factory=lambda: OutputOptions(output_dir=Path.home() / "Pictures" / "ContextHub_Exports")
    )
