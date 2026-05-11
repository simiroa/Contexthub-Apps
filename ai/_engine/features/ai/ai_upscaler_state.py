from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


MODEL_CHOICES: tuple[tuple[str, str, str], ...] = (
    ("esrgan", "Real-ESRGAN", "esrgan.json"),
    ("diffbir", "DiffBIR-v2", "diffbir.json"),
    ("supir", "SUPIR", "supir.json"),
)


@dataclass
class InputAsset:
    path: Path
    kind: str = "image"


@dataclass
class OutputOptions:
    output_dir: Path | None = None
    file_prefix: str = "upscaled"
    open_folder_after_run: bool = True
    export_session_json: bool = False


@dataclass
class AIUpscalerState:
    model_key: str = "esrgan"
    scale: str = "4"
    seed: int = 0
    use_seed: bool = False
    preview_path: Path | None = None
    input_assets: list[InputAsset] = field(default_factory=list)
    parameter_values: dict[str, object] = field(default_factory=dict)
    output_options: OutputOptions = field(default_factory=OutputOptions)
