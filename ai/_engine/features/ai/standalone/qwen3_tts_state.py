from dataclasses import dataclass, field


@dataclass
class MessageState:
    id: str
    role: str
    profile: str
    tone: str
    text: str
    status: str = "ready"
    output: str = ""


@dataclass
class AppState:
    selected_message_id: str | None = None
    expanded_actions_message_id: str | None = None
    editing_text_message_id: str | None = None
    profile_panel_open: bool = False
    current_playback_path: str | None = None
    overlay_open: bool = False
    overlay_title: str = "Preparing generation..."
    overlay_hint: str = ""
    overlay_progress: float = 0.0
    status_text: str = "Ready"
    messages: list[MessageState] = field(default_factory=list)
