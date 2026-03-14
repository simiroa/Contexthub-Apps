from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass
class VideoInterpState:
    input_path: Optional[Path] = None
    multiplier: str = "2x"
    quality_mode: str = "mci"
    
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    last_output: Optional[Path] = None
    error_message: Optional[str] = None
