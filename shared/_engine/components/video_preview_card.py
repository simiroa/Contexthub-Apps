from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget

from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.preview_card_base import build_preview_card_base


def build_video_preview_card(title: str = "Video Preview") -> dict[str, object]:
    footer = QWidget()
    meta_row = QHBoxLayout()
    meta_row.setContentsMargins(0, 0, 0, 0)
    meta_label = QLabel("Duration / resolution / fps")
    meta_label.setObjectName("summaryText")
    meta_row.addWidget(meta_label, 1)
    play_btn = build_icon_button("Play", icon_name="play", role="primary")
    meta_row.addWidget(play_btn, 0)
    footer.setLayout(meta_row)

    result = build_preview_card_base(
        title,
        "Thumbnail / player surface",
        "",
        surface_key="viewport",
        min_height=160,
        footer=footer,
    )
    result["meta_label"] = meta_label
    result["play_btn"] = play_btn
    return result
