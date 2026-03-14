from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class ResizePotState:
    files: List[Path] = field(default_factory=list)
    target_size: str = "1024"
    force_square: bool = True
    mode: str = "Standard"  # "Standard" or "AI"
    save_to_folder: bool = False
    delete_original: bool = False
    
    # UI related
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    cancel_flag: bool = False
