from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_button_role, set_surface_role


def build_video_preview_card(title: str = "Video Preview") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    viewport = QFrame()
    set_surface_role(viewport, "subtle")
    viewport.setMinimumHeight(160)
    viewport_layout = QVBoxLayout(viewport)
    viewport_layout.setContentsMargins(10, 10, 10, 10)
    viewport_label = QLabel("Thumbnail / player surface")
    viewport_label.setAlignment(Qt.AlignCenter)
    viewport_layout.addWidget(viewport_label, 1)
    layout.addWidget(viewport)

    meta_row = QHBoxLayout()
    meta_label = QLabel("Duration / resolution / fps")
    meta_label.setObjectName("summaryText")
    meta_row.addWidget(meta_label, 1)
    play_btn = QPushButton("Play")
    set_button_role(play_btn, "primary")
    meta_row.addWidget(play_btn, 0)
    layout.addLayout(meta_row)

    return {
        "card": card,
        "viewport": viewport,
        "meta_label": meta_label,
        "play_btn": play_btn,
    }
