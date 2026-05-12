from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

WORKFLOW_CHOICES: tuple[tuple[str, str, str], ...] = (
    ("global", "Global Enhance", "global.json"),
    ("detail", "Painted Detail", "detail.json"),
    ("face", "Face Boost", "face.json"),
    ("repair", "Repair Pass", "repair.json"),
)


@dataclass
class InputAsset:
    path: Path
    kind: str = "image"
    mask_path: Path | None = None


@dataclass
class EnhanceLayer:
    name: str
    enabled: bool = True
    workflow_key: str = "detail"
    strength: float = 0.65
    opacity: float = 1.0
    use_mask: bool = True
    invert_mask: bool = False


@dataclass
class OutputOptions:
    output_dir: Path | None = None
    file_prefix: str = "enhanced"
    open_folder_after_run: bool = True
    export_session_json: bool = True


@dataclass
class ImageEnhancerState:
    selected_input_index: int = -1
    preview_path: Path | None = None
    input_assets: list[InputAsset] = field(default_factory=list)
    layers: list[EnhanceLayer] = field(
        default_factory=lambda: [
            EnhanceLayer(name="Base Clean-up", workflow_key="global", strength=0.45, use_mask=False),
            EnhanceLayer(name="Painted Detail", workflow_key="detail", strength=0.70, use_mask=True),
        ]
    )
    selected_layer_index: int = 0
    scale: str = "4"
    seed: int = 0
    use_seed: bool = False
    parameter_values: dict[str, object] = field(default_factory=dict)
    active_mask_path: Path | None = None
    output_options: OutputOptions = field(default_factory=OutputOptions)
