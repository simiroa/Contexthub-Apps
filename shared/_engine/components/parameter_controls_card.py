from __future__ import annotations

from typing import Optional, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from contexthub.ui.qt.shell import get_shell_metrics, get_shell_palette
from shared._engine.components.parameter_row import ParameterRow


class ParameterCard(QFrame):
    """
    Standardized Parameter Card for Contexthub-Apps.
    Enforces a consistent layout using ParameterRow and unified styling.
    """
    
    def __init__(self, title: str = "Parameters", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.m = get_shell_metrics()
        self.p = get_shell_palette()
        self.setObjectName("card")
        self._init_ui(title)

    def _init_ui(self, title: str):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(self.m.panel_padding, self.m.panel_padding, self.m.panel_padding, self.m.panel_padding)
        self.layout.setSpacing(self.m.section_gap)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        self.layout.addWidget(self.title_label)

        # Container for rows
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 4, 0, 4)
        self.rows_layout.setSpacing(10)
        self.layout.addWidget(self.rows_container)

    def add_row(self, label: str, widget: QWidget) -> ParameterRow:
        row = ParameterRow(label, widget)
        self.rows_layout.addWidget(row)
        return row

    def add_checkbox(self, label: str) -> QCheckBox:
        cb = QCheckBox(label)
        self.layout.addWidget(cb)
        return cb


def build_parameter_controls_card(title: str = "Parameters") -> dict[str, object]:
    card_obj = ParameterCard(title)
    
    # Generic example setup for compatibility
    profile_combo = QComboBox()
    profile_combo.setObjectName("compactField")
    card_obj.add_row("Profile", profile_combo)
    
    scale_combo = QComboBox()
    scale_combo.setObjectName("compactField")
    card_obj.add_row("Scale", scale_combo)

    # Slider row (custom layout for slider + value)
    slider_field = QWidget()
    slider_layout = QHBoxLayout(slider_field)
    slider_layout.setContentsMargins(0, 0, 0, 0)
    slider_layout.setSpacing(8)
    
    slider = QSlider(Qt.Horizontal)
    slider_value = QLabel("0")
    slider_value.setFixedWidth(24)
    slider_value.setObjectName("summaryText")
    
    slider_layout.addWidget(slider, 1)
    slider_layout.addWidget(slider_value)
    card_obj.add_row("Strength", slider_field)

    smart_toggle = card_obj.add_checkbox("Use smart defaults")

    return {
        "card": card_obj,
        "profile_combo": profile_combo,
        "scale_combo": scale_combo,
        "slider": slider,
        "slider_value": slider_value,
        "smart_toggle": smart_toggle,
    }
