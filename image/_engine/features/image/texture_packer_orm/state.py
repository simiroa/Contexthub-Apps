from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class SlotState:
    path: Optional[Path] = None
    label: str = ""
    preview_base64: Optional[str] = None

@dataclass
class PackerState:
    slots: Dict[str, SlotState] = field(default_factory=lambda: {
        "r": SlotState(),
        "g": SlotState(),
        "b": SlotState(),
        "a": SlotState()
    })
    
    output_name: str = "_Packed"
    output_format: str = ".png"
    resize_enabled: bool = False
    resize_value: str = "2048"
    current_preset: str = "ORM"
    
    # UI state
    is_processing: bool = False
    status_text: str = "Ready"
