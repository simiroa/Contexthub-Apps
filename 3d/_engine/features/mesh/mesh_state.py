from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MeshAppState:
    mode: str = "convert"  # convert, cad, extract, mayo
    input_paths: list[Path] = field(default_factory=list)
    selected_index: int = -1
    output_format: str = "OBJ"
    convert_to_subfolder: bool = True
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    last_output: Path | None = None
    error_message: str | None = None
