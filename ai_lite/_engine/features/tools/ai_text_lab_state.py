from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class AITextLabState:
    # App Config
    available_models: List[str] = field(default_factory=list)
    current_model: str = "qwen3:8b"
    current_preset: str = "🔍 Grammar Fix"
    
    # Text State
    input_text: str = ""
    output_text: str = ""
    status_msg: str = "Ready"
    
    # UI/Settings State
    is_pinned: bool = False
    is_auto_clip: bool = False
    opacity: float = 1.0
    think_mode: str = "Auto" # Auto, On, Off
    
    # Processing State
    is_processing: bool = False
    is_streaming: bool = False
    gemini_cooldown_until: float = 0
    request_counter: int = 0
    
    def get_effective_think_mode(self, preset_think_default: bool) -> bool:
        if self.think_mode == "On":
            return True
        if self.think_mode == "Off":
            return False
        return preset_think_default
