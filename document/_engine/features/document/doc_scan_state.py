from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class ScanItem:
    """Represents a single document page."""
    path: Path
    image: np.ndarray
    rotation: int = 0
    filter_type: str = "orig"  # orig | bw | magic
    
    # Perspective corners: [(x, y), (x, y), (x, y), (x, y)]
    # Normalized 0.0 to 1.0 relative to image size
    corners: Optional[List[Tuple[float, float]]] = None
    unwarp_active: bool = False
    
    # Signature overlay for this specific item
    signature_pos: Optional[Tuple[float, float]] = None  # Normalized center pos
    signature_scale: float = 0.2  # Relative to image width


@dataclass
class DocScanState:
    # Documents
    items: List[ScanItem] = field(default_factory=list)
    current_index: int = -1
    
    # Global Signature (can be applied to any item)
    signature_image: Optional[np.ndarray] = None
    signature_path: Optional[Path] = None
    
    # UI State
    status_text: str = "Ready"
    is_processing: bool = False
    progress_value: float = 0.0
    
    # Output
    save_to_folder: bool = True
    custom_output_dir: Optional[Path] = None
    
    # Matching template structure for UI compatibility
    parameter_values: dict = field(default_factory=lambda: {
        "filter": "orig"
    })
