from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass
class AudioSeparateState:
    input_paths: List[Path] = field(default_factory=list)
    model: str = "htdemucs"
    output_format: str = "mp3"
    separation_mode: str = "All Stems (4)"
    
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    last_output_dir: Optional[Path] = None
    
    error_message: Optional[str] = None
