import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class ImageCompareState:
    files: List[Path] = field(default_factory=list)
    current_channel: str = "RGB"
    current_mode: str = "Side by Side"
    zoom_level: float = 1.0
    pan_offset: List[float] = field(default_factory=lambda: [0.0, 0.0])
    slider_pos: float = 0.5
    slots: dict = field(default_factory=lambda: {"A": 0, "B": 0})
    active_slot: str = "A"
    
    # UI related states
    available_channels: List[str] = field(default_factory=lambda: ["RGB", "R", "G", "B", "A"])
    ssim_score: Optional[float] = None
    diff_pixels: Optional[int] = None
    
    def reset_view(self):
        self.zoom_level = 1.0
        self.pan_offset = [0.0, 0.0]
