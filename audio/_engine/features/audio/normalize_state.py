from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass
class AudioNormalizeState:
    input_paths: List[Path] = field(default_factory=list)
    target_loudness: float = -16.0
    true_peak: float = -1.5
    loudness_range: float = 11.0
    
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    last_output_path: Optional[Path] = None
    
    error_message: Optional[str] = None
