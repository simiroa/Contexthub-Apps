from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OutputOptions:
    output_dir: Path
    file_prefix: str = "z_turbo"
    open_folder_after_run: bool = True
    export_session_json: bool = True


@dataclass
class CreativeStudioZState:
    workflow_name: str = ""
    workflow_description: str = ""
    status_text: str = "Ready"
    status_level: str = "ready"
    preview_path: Path | None = None
    recent_files: list[Path] = field(default_factory=list)
    parameter_values: dict[str, Any] = field(default_factory=dict)
    output_options: OutputOptions = field(
        default_factory=lambda: OutputOptions(output_dir=Path.home() / "Pictures" / "ContextHub_Exports")
    )
