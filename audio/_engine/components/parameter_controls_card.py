from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics


def build_parameter_controls_card(title: str = "Parameters") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    profile_row = QHBoxLayout()
    profile_row.setSpacing(8)
    profile_row.addWidget(QLabel("Profile"))
    profile_combo = QComboBox()
    profile_row.addWidget(profile_combo, 1)
    layout.addLayout(profile_row)

    scale_row = QHBoxLayout()
    scale_row.setSpacing(8)
    scale_row.addWidget(QLabel("Scale"))
    scale_combo = QComboBox()
    scale_row.addWidget(scale_combo, 1)
    layout.addLayout(scale_row)

    slider_row = QHBoxLayout()
    slider_row.setSpacing(8)
    slider_label = QLabel("Strength")
    slider_value = QLabel("0")
    slider = QSlider(Qt.Horizontal)
    slider_row.addWidget(slider_label, 0)
    slider_row.addWidget(slider, 1)
    slider_row.addWidget(slider_value, 0)
    layout.addLayout(slider_row)

    smart_toggle = QCheckBox("Use smart defaults")
    layout.addWidget(smart_toggle)

    return {
        "card": card,
        "profile_combo": profile_combo,
        "scale_combo": scale_combo,
        "slider": slider,
        "slider_value": slider_value,
        "smart_toggle": smart_toggle,
    }
