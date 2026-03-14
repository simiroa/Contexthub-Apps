from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass
class MeshAppState:
    mode: str = "convert"  # convert, cad, bake, extract, lod, mayo
    input_paths: List[Path] = field(default_factory=list)
    output_format: str = "OBJ"
    
    # Options
    lod_ratio: float = 0.5
    bake_maps: List[str] = field(default_factory=lambda: ["Diffuse", "Normal"])
    target_scale: float = 1.0
    
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    last_output: Optional[Path] = None
    error_message: Optional[str] = None
