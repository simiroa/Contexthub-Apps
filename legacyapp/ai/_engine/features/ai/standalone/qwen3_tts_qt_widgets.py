from __future__ import annotations

import wave
from pathlib import Path

from contexthub.ui.qt.shell import get_shell_accent_cycle, get_shell_palette

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for qwen3_tts.") from exc


def status_text(status: str) -> str:
    return {"ready": "Ready", "queued": "Queued", "done": "Done", "error": "Error"}.get(status, status)


def status_color(status: str) -> str:
    p = get_shell_palette()
    return {
        "ready": p.text_muted,
        "queued": p.warning,
        "done": p.success,
        "error": p.error,
    }.get(status, p.text)


def safe_prefix(value: str, limit: int = 80) -> str:
    normalized = (value or "").strip().replace("\n", " ")
    return normalized if len(normalized) <= limit else f"{normalized[:limit-1].rstrip()}…"


def profile_accent(name: str) -> str:
    accents = get_shell_accent_cycle()
    return accents[sum(ord(ch) for ch in (name or "profile")) % len(accents)]


def initials(name: str) -> str:
    parts = [part for part in (name or "").replace("_", " ").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[1][0]}".upper()


def duration_text(path: str) -> str:
    if not path:
        return ""
    try:
        output = Path(path)
        if output.suffix.lower() != ".wav" or not output.exists():
            return ""
        with wave.open(str(output), "rb") as wav_file:
            duration = wav_file.getnframes() / max(1, wav_file.getframerate())
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}:{seconds:02d}"
    except Exception:
        return ""


class MessageBubbleWidget(QFrame):
    select_requested = Signal(str)
    expand_requested = Signal(str)
    apply_requested = Signal(str, str, str, str)
    play_requested = Signal(str)
    open_requested = Signal(str)
    profile_requested = Signal(str)
    regenerate_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, message, profiles: list[str], selected: bool = False, expanded: bool = False, media_enabled: bool = False) -> None:
        super().__init__()
        self.message_id = message.id
        self.setObjectName("messageBubbleRoot")
        p = get_shell_palette()
        accent = profile_accent(message.profile)
        bubble_bg = p.status_card_bg if not selected else p.card_bg
        border = accent if selected else p.control_border
        self.setStyleSheet(
            f"""
            QFrame#messageBubbleRoot {{
                background: transparent;
                border: none;
            }}
            QLabel#avatar {{
                background: {accent};
                color: {p.app_bg};
                border-radius: 20px;
                font-size: 13px;
                font-weight: 700;
            }}
            QFrame#bubble {{
                background: {bubble_bg};
                border: 1px solid {border};
                border-radius: 18px;
            }}
            QLabel#name {{
                color: {p.text};
                font-size: 14px;
                font-weight: 700;
            }}
            QLabel#time {{
                color: {p.text_muted};
                font-size: 11px;
            }}
            QLabel#body {{
                color: {p.text};
                font-size: 15px;
                line-height: 1.35;
            }}
            QLabel#mini {{
                color: {accent};
                font-size: 17px;
                font-weight: 700;
            }}
            QLabel#meta {{
                color: {p.text_muted};
                font-size: 11px;
            }}
            QPushButton#expandBtn {{
                background: transparent;
                color: {p.text_muted};
                border: none;
                font-size: 13px;
                font-weight: 700;
                padding: 2px 4px;
            }}
            QPushButton#ghostBtn {{
                background: {p.control_bg};
                color: {p.text};
                border: 1px solid {p.control_border};
                border-radius: 12px;
                padding: 6px 10px;
            }}
            QPushButton#ghostBtn:hover {{
                background: {p.button_hover};
            }}
            QLabel#chip {{
                background: {p.button_bg};
                border-radius: 10px;
                color: {status_color(message.status)};
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 700;
            }}
            """
        )
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 4)
        root.setSpacing(12)

        avatar = QLabel(initials(message.profile))
        avatar.setObjectName("avatar")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(40, 40)
        root.addWidget(avatar, 0, Qt.AlignTop)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(6)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(8)
        name = QLabel(message.profile)
        name.setObjectName("name")
        meta_row.addWidget(name, 0)
        clock = QLabel(message.id.replace("msg_", ""))
        clock.setObjectName("time")
        meta_row.addWidget(clock, 0)
        meta_row.addStretch(1)
        expand_btn = QPushButton("▾" if expanded else "▸")
        expand_btn.setObjectName("expandBtn")
        expand_btn.clicked.connect(lambda: self.expand_requested.emit(self.message_id))
        meta_row.addWidget(expand_btn, 0)
        status_chip = QLabel(status_text(message.status))
        status_chip.setObjectName("chip")
        meta_row.addWidget(status_chip, 0)
        content.addLayout(meta_row)

        bubble = QFrame()
        bubble.setObjectName("bubble")
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(18, 16, 18, 14)
        bubble_layout.setSpacing(12)

        body = QLabel(message.text)
        body.setObjectName("body")
        body.setWordWrap(True)
        body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bubble_layout.addWidget(body)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(10)
        mini_play = QLabel("▶")
        mini_play.setObjectName("mini")
        mini_play.setFixedWidth(16)
        bottom_row.addWidget(mini_play, 0)
        meter = QLabel("▁▃▆▂▅")
        meter.setObjectName("mini")
        bottom_row.addWidget(meter, 0)
        bottom_row.addStretch(1)
        tone = QLabel(message.tone.title())
        tone.setObjectName("meta")
        bottom_row.addWidget(tone, 0)
        duration = QLabel(duration_text(message.output))
        duration.setObjectName("meta")
        bottom_row.addWidget(duration, 0)
        bubble_layout.addLayout(bottom_row)

        self.details = QFrame()
        details_layout = QVBoxLayout(self.details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(10)

        self.profile_combo = QPushButton(message.profile)
        self.profile_combo.setObjectName("ghostBtn")
        self.profile_combo.clicked.connect(lambda: self.profile_requested.emit(self.message_id))
        details_layout.addWidget(self.profile_combo)

        self.tone_label = QLabel(f"Tone: {message.tone}")
        self.tone_label.setObjectName("meta")
        details_layout.addWidget(self.tone_label)

        self.summary_label = QLabel(safe_prefix(message.text, 220))
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("meta")
        details_layout.addWidget(self.summary_label)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)
        self.select_btn = QPushButton("Select")
        self.select_btn.setObjectName("ghostBtn")
        self.select_btn.clicked.connect(lambda: self.select_requested.emit(self.message_id))
        action_row.addWidget(self.select_btn)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("ghostBtn")
        self.apply_btn.clicked.connect(
            lambda: self.apply_requested.emit(self.message_id, message.profile, message.tone, message.text)
        )
        action_row.addWidget(self.apply_btn)
        self.regenerate_btn = QPushButton("Re-run")
        self.regenerate_btn.setObjectName("ghostBtn")
        self.regenerate_btn.clicked.connect(lambda: self.regenerate_requested.emit(self.message_id))
        action_row.addWidget(self.regenerate_btn)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("ghostBtn")
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.message_id))
        action_row.addWidget(self.delete_btn)
        details_layout.addLayout(action_row)

        output_row = QHBoxLayout()
        output_row.setContentsMargins(0, 0, 0, 0)
        output_row.setSpacing(8)
        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("ghostBtn")
        self.play_btn.setEnabled(media_enabled and bool(message.output))
        self.play_btn.clicked.connect(lambda: self.play_requested.emit(self.message_id))
        output_row.addWidget(self.play_btn)
        self.open_btn = QPushButton("Open")
        self.open_btn.setObjectName("ghostBtn")
        self.open_btn.setEnabled(bool(message.output))
        self.open_btn.clicked.connect(lambda: self.open_requested.emit(self.message_id))
        output_row.addWidget(self.open_btn)
        details_layout.addLayout(output_row)

        self.details.setVisible(expanded)
        bubble_layout.addWidget(self.details)
        content.addWidget(bubble)
        root.addLayout(content, 1)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.select_requested.emit(self.message_id)
        super().mousePressEvent(event)
