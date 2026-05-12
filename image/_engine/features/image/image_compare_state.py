from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class ComparisonSlotState:
    """State for a single comparison slot (A or B)."""
    path: Optional[Path] = None
    channel: str = "RGB"
    ssim_score: Optional[float] = None
    diff_pixels: Optional[int] = None
    is_loading: bool = False


@dataclass
class ImageCompareState:
    """Top-level state with mode-driven architecture."""
    # Visualization mode
    mode: str = "split"  # split, grid, diff, single

    # Comparison slots
    slot_a: ComparisonSlotState = field(default_factory=ComparisonSlotState)
    slot_b: ComparisonSlotState = field(default_factory=ComparisonSlotState)

    # File management
    files: List[Path] = field(default_factory=list)

    # Viewport state
    viewport_width: int = 800
    viewport_height: int = 600
    slider_ratio: float = 0.5  # 0.0 (left) to 1.0 (right) for split mode

    # Processing state
    is_processing: bool = False
    status_text: str = "Ready"

