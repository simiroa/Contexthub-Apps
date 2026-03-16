from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class SlotState:
    path: Optional[Path] = None
    label: str = ""
    preview_base64: Optional[str] = None
    invert: bool = False

@dataclass
class PackerState:
    slots: Dict[str, SlotState] = field(default_factory=lambda: {
        "r": SlotState(label="AO"),
        "g": SlotState(label="Roughness"),
        "b": SlotState(label="Metallic"),
        "a": SlotState(label="Alpha")
    })
    
    output_name: str = "_Packed"
    output_format: str = ".png"
    resize_enabled: bool = False
    resize_value: str = "2048"
    current_preset: str = "ORM"
    
    presets: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "ORM": {"r": "AO", "g": "Roughness", "b": "Metallic", "a": "Alpha"},
        "Unity (Mask)": {"r": "Metallic", "g": "Occlusion", "b": "Detail", "a": "Smoothness"},
        "Unreal (ORM)": {"r": "Occlusion", "g": "Roughness", "b": "Metallic", "a": "Alpha"},
        "Custom": {"r": "Red", "g": "Green", "b": "Blue", "a": "Alpha"}
    })
    
    # UI state
    is_processing: bool = False
    status_text: str = "Ready"
