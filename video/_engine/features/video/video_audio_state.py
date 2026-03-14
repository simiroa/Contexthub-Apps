from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

@dataclass
class VideoAudioState:
    files: List[Path] = field(default_factory=list)
    mode: str = "extract"  # "extract", "remove", "separate"
    extract_format: str = "MP3"  # "MP3", "WAV"
    separate_mode: str = "Voice"  # "Voice", "BGM"
    save_to_folder: bool = True
    
    # Progress
    is_processing: bool = False
    progress_value: float = 0.0
    status_text: str = "Ready"
    completed_count: int = 0
    total_count: int = 0
    cancel_flag: bool = False
    
    # Environment
    ffmpeg_path: Optional[str] = None
