from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class ChannelConfig:
    source_file: Optional[str] = None
    target_name: str = ""
    mode: str = "RGB"  # RGB, RGBA, R, G, B, A, L
    invert: bool = False
    linear: bool = False
    enabled: bool = True

@dataclass
class ExrMergeState:
    files: List[Path] = field(default_factory=list)
    channels: List[ChannelConfig] = field(default_factory=list)
    common_prefix: str = ""
    
    # UI related
    is_exporting: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    output_path: Optional[Path] = None
