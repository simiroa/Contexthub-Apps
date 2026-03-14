from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class NormalFlipState:
    files: List[Path] = field(default_factory=list)
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    results: List[str] = field(default_factory=list)
