from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass
class AudioConvertState:
    input_paths: List[Path] = field(default_factory=list)
    output_format: str = "MP3"
    quality: str = "High"
    copy_metadata: bool = True
    save_to_new_folder: bool = True
    delete_original: bool = False
    
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    last_converted: Optional[Path] = None
    
    error_message: Optional[str] = None
