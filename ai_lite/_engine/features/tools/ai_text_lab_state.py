from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class AITextLabState:
    # App Config
    available_models: List[str] = field(default_factory=list)
    current_model: str = "qwen3:4b"
    current_preset: str = "🔍 Grammar Fix"
    presets: Dict[str, str] = field(default_factory=dict)
    
    # Text State
    input_text: str = ""
    output_text: str = ""
    status_msg: str = "Ready"
    
    # History Memory
    history: List[Dict] = field(default_factory=list)
    
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
    
    def add_to_history(self, input_text: str, output_text: str, model: str, preset: str):
        self.history.insert(0, {
            "input": input_text,
            "output": output_text,
            "model": model,
            "preset": preset
        })
        if len(self.history) > 100:
            self.history.pop()

    def get_effective_think_mode(self, preset_think_default: bool) -> bool:
        if self.think_mode == "On":
            return True
        if self.think_mode == "Off":
            return False
        return preset_think_default
