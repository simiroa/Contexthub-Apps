from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass
class MeshAppState:
    mode: str = "convert"  # convert, cad, bake, extract, lod, mayo
    input_paths: List[Path] = field(default_factory=list)
    selected_index: int = -1
    output_format: str = "OBJ"
    
    # Options
    lod_ratio: float = 0.5
    lod_count: int = 3
    convert_to_subfolder: bool = True
    bake_maps: List[str] = field(default_factory=lambda: ["Diffuse", "Normal"])
    target_faces: int = 10000
    target_scale: float = 1.0
    preserve_uv: bool = True
    preserve_normal: bool = True
    preserve_boundary: bool = True
    bake_size: int = 2048
    bake_ray_dist: float = 0.1
    bake_margin: int = 16
    bake_flip_green: bool = False
    bake_diffuse: bool = False
    bake_orm_pack: bool = False
    
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    last_output: Optional[Path] = None
    error_message: Optional[str] = None
