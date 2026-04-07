from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout
from PySide6.QtCore import Qt

from contexthub.ui.qt.shell import get_shell_metrics


def build_parameter_strip(title: str = "Parameter") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    row = QHBoxLayout()
    value_label = QLabel("0")
    slider = QSlider(Qt.Horizontal)
    row.addWidget(value_label, 0)
    row.addWidget(slider, 1)
    layout.addWidget(title_label)
    layout.addLayout(row)
    return {"card": card, "slider": slider, "value_label": value_label}
