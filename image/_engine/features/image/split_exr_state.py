from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class LayerConfig:
    name: str
    enabled: bool = True
    invert: bool = False
    suffix: str = ""
    channels: List[str] = field(default_factory=list)

@dataclass
class SplitExrState:
    files: List[Path] = field(default_factory=list)
    layers: List[LayerConfig] = field(default_factory=list)
    output_format: str = "PNG"
    
    # UI state
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    
    # Primary file info (for display)
    primary_info: str = ""
