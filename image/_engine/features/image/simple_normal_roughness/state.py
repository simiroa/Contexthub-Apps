from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class PbrGenState:
    files: List[Path] = field(default_factory=list)
    preview_mode: str = "Normal"  # "Original", "Normal", "Roughness"
    
    # Normal Parameters
    normal_strength: float = 1.0
    normal_flip_g: bool = False
    
    # Roughness Parameters
    roughness_contrast: float = 1.0
    roughness_invert: bool = False
    
    # UI state
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
