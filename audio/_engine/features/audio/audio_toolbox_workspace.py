from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QSlider, QVBoxLayout

from contexthub.ui.qt.shell import ElidedLabel, set_surface_role
from shared._engine.components.icon_button import build_icon_button


def build_player_card() -> dict[str, object]:
    card = QFrame()
    set_surface_role(card, "subtle")
    card.setMaximumHeight(176)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    player_title = QLabel("Selected Audio")
    player_title.setObjectName("eyebrow")
    now_playing = ElidedLabel("No selection")
    now_playing.setObjectName("title")
    audio_path = ElidedLabel("")
    audio_path.setObjectName("summaryText")

    name_row = QHBoxLayout()
    name_row.setContentsMargins(0, 0, 0, 0)
    name_row.setSpacing(8)
    name_row.addWidget(now_playing, 1)
    name_row.addWidget(player_title, 0, Qt.AlignRight | Qt.AlignVCenter)
    layout.addLayout(name_row)
    layout.addWidget(audio_path)

    transport = QHBoxLayout()
    transport.setContentsMargins(0, 0, 0, 0)
    transport.setSpacing(6)
    play_btn = build_icon_button("Play", icon_name="play", role="subtle")
    pause_btn = build_icon_button("Pause", icon_name="pause", role="subtle")
    time_label = QLabel("0:00 / 0:00")
    time_label.setObjectName("muted")
    transport.addWidget(play_btn, 0)
    transport.addWidget(pause_btn, 0)
    transport.addWidget(time_label, 1)
    layout.addLayout(transport)

    position_slider = QSlider(Qt.Horizontal)
    position_slider.setRange(0, 0)
    layout.addWidget(position_slider)

    return {
        "card": card,
        "now_playing": now_playing,
        "audio_path": audio_path,
        "play_btn": play_btn,
        "pause_btn": pause_btn,
        "time_label": time_label,
        "position_slider": position_slider,
    }


def build_queue_card() -> dict[str, object]:
    card = QFrame()
    set_surface_role(card, "subtle")

    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    title = QLabel("Queued Audio")
    title.setObjectName("sectionTitle")
    layout.addWidget(title)

    file_list = QListWidget()
    file_list.setMinimumHeight(200)
    layout.addWidget(file_list, 1)

    action_row = QHBoxLayout()
    action_row.setContentsMargins(0, 0, 0, 0)
    action_row.setSpacing(6)
    add_btn = build_icon_button("Add", icon_name="plus", role="secondary")
    remove_btn = build_icon_button("Remove", icon_name="minus", role="secondary")
    clear_btn = build_icon_button("Clear", icon_name="trash-2", role="secondary")
    pick_output_btn = build_icon_button("Output Folder", icon_name="folder", role="secondary")
    for button in (add_btn, remove_btn, clear_btn, pick_output_btn):
        action_row.addWidget(button)
    layout.addLayout(action_row)

    return {
        "card": card,
        "file_list": file_list,
        "add_btn": add_btn,
        "remove_btn": remove_btn,
        "clear_btn": clear_btn,
        "pick_output_btn": pick_output_btn,
    }
