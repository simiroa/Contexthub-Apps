from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role
from shared._engine.components.icon_button import build_icon_button


def build_audio_preview_card(title: str = "Audio Preview") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    waveform = QFrame()
    set_surface_role(waveform, "subtle")
    waveform.setMinimumHeight(84)
    waveform_layout = QVBoxLayout(waveform)
    waveform_layout.setContentsMargins(10, 10, 10, 10)
    waveform_label = QLabel("Waveform / audio preview")
    waveform_label.setAlignment(Qt.AlignCenter)
    waveform_layout.addWidget(waveform_label, 1)
    layout.addWidget(waveform)

    meta_label = QLabel("Duration / sample rate / channels")
    meta_label.setObjectName("summaryText")
    layout.addWidget(meta_label)

    controls = QHBoxLayout()
    play_btn = build_icon_button("Play", icon_name="play", role="primary")
    stop_btn = build_icon_button("Stop", icon_name="square", role="secondary")
    controls.addWidget(play_btn)
    controls.addWidget(stop_btn)
    controls.addStretch(1)
    layout.addLayout(controls)

    meter = QProgressBar()
    meter.setRange(0, 100)
    meter.setValue(0)
    layout.addWidget(meter)

    return {
        "card": card,
        "waveform": waveform,
        "meta_label": meta_label,
        "play_btn": play_btn,
        "stop_btn": stop_btn,
        "meter": meter,
    }
