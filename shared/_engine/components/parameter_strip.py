from __future__ import annotations

from PySide6.QtWidgets import QLabel, QSlider, QWidget, QHBoxLayout
from PySide6.QtCore import Qt

from shared._engine.components.parameter_controls_card import ParameterCard


def build_parameter_strip(title: str = "Parameter") -> dict[str, object]:
    card = ParameterCard(title)
    slider_field = QWidget()
    row = QHBoxLayout(slider_field)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    value_label = QLabel("0")
    value_label.setObjectName("summaryText")
    slider = QSlider(Qt.Horizontal)
    row.addWidget(value_label, 0)
    row.addWidget(slider, 1)
    card.add_row("Value", slider_field)
    return {"card": card, "slider": slider, "value_label": value_label}
