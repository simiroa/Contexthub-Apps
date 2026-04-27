from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QWidget

from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.preview_card_base import build_preview_card_base


def build_audio_preview_card(title: str = "Audio Preview") -> dict[str, object]:
    footer = QWidget()
    controls = QHBoxLayout()
    controls.setContentsMargins(0, 0, 0, 0)
    play_btn = build_icon_button("Play", icon_name="play", role="primary")
    stop_btn = build_icon_button("Stop", icon_name="square", role="secondary")
    controls.addWidget(play_btn)
    controls.addWidget(stop_btn)
    controls.addStretch(1)
    footer.setLayout(controls)

    meter = QProgressBar()
    meter.setRange(0, 100)
    meter.setValue(0)

    result = build_preview_card_base(
        title,
        "Waveform / audio preview",
        "Duration / sample rate / channels",
        surface_key="waveform",
        min_height=84,
        footer=footer,
    )
    result["meta_label"] = result.pop("meta")
    result["play_btn"] = play_btn
    result["stop_btn"] = stop_btn
    result["meter"] = meter
    result["card"].layout().addWidget(meter)
    return result
