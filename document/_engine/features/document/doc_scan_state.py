from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class DocScanState:
    image_path: Optional[Path] = None
    image: Optional[np.ndarray] = None
    # Normalized (0.0–1.0) corner positions: TL, TR, BR, BL
    corners: List[Tuple[float, float]] = field(default_factory=lambda: [
        (0.05, 0.05), (0.95, 0.05), (0.95, 0.95), (0.05, 0.95)
    ])
    # Signature overlay (BGRA format with transparency)
    signature_image: Optional[np.ndarray] = None
    signature_path: Optional[Path] = None
    # Normalized position (0.0-1.0) and scale, opacity (0-100)
    signature_x: float = 0.7
    signature_y: float = 0.85
    signature_scale: float = 0.2
    signature_opacity: int = 100
    # Blend mode for compositing the signature: "normal", "multiply", "darken"
    signature_blend_mode: str = "multiply"
    # Grayscale filter toggle
    is_grayscale: bool = False
