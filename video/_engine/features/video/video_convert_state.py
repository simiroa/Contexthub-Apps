from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

@dataclass
class VideoConvertState:
    files: List[Path] = field(default_factory=list)
    output_format: str = "MP4 (H.264 NVENC)"
    scale: str = "100%"
    custom_width: str = ""
    crf: int = 23
    save_to_folder: bool = False
    custom_output_dir: Optional[Path] = None
    delete_original: bool = False
    
    # Progress state
    is_processing: bool = False
    progress_value: float = 0.0
    status_text: str = "Ready"
    completed_count: int = 0
    total_count: int = 0
    cancel_flag: bool = False
    
    # Environment
    has_nvenc: bool = False
    ffmpeg_path: Optional[str] = None
