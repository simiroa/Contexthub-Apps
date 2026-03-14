from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class ImageConvertState:
    files: List[Path] = field(default_factory=list)
    target_format: str = "PNG"
    resize_enabled: bool = False
    resize_size: str = "1024"
    save_to_folder: bool = False
    delete_original: bool = False
    
    # UI related states
    is_converting: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    errors: List[str] = field(default_factory=list)
    completed_count: int = 0
    total_count: int = 0
