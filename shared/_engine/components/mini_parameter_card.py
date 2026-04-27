from __future__ import annotations

from typing import Optional, Dict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from contexthub.ui.qt.shell import get_shell_metrics


class MiniParameterCard(QFrame):
    """
    Ultra-compact Parameter Card for 'mini' apps.
    Features a top-aligned eyebrow label and status display with a full-width slider.
    """
    
    def __init__(
        self,
        label: str,
        min_val: int = 0,
        max_val: int = 2,
        default_val: int = 1,
        value_labels: Optional[Dict[int, str]] = None,
        *,
        embedded: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.m = get_shell_metrics()
        self._embedded = embedded
        if not embedded:
            self.setObjectName("card")
        self._init_ui(label, min_val, max_val, default_val, value_labels)

    def _init_ui(self, label: str, min_val: int, max_val: int, default_val: int, value_labels: Optional[Dict[int, str]]):
        self.layout = QVBoxLayout(self)
        horizontal_margin = 0 if self._embedded else self.m.panel_padding
        self.layout.setContentsMargins(horizontal_margin, 8, horizontal_margin, 10)
        self.layout.setSpacing(4)
        
        # Header Row (Label + Value)
        label_row = QHBoxLayout()
        label_row.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(label.upper())
        self.title_label.setObjectName("eyebrow")
        
        self.value_display = QLabel("")
        self.value_display.setObjectName("summaryText")
        
        label_row.addWidget(self.title_label)
        label_row.addStretch()
        label_row.addWidget(self.value_display)
        self.layout.addLayout(label_row)
        
        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default_val)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.setFixedHeight(22)
        self.layout.addWidget(self.slider)
        
        # Logic
        def update_label(val: int):
            if value_labels and val in value_labels:
                self.value_display.setText(value_labels[val])
            else:
                self.value_display.setText(str(val))
                
        self.slider.valueChanged.connect(update_label)
        update_label(default_val)


def build_mini_parameter_slider(
    label: str, 
    min_val: int = 0, 
    max_val: int = 2, 
    default_val: int = 1,
    value_labels: dict[int, str] | None = None,
    *,
    embedded: bool = False,
) -> dict[str, object]:
    card_obj = MiniParameterCard(
        label,
        min_val,
        max_val,
        default_val,
        value_labels,
        embedded=embedded,
    )
    
    return {
        "card": card_obj,
        "slider": card_obj.slider,
        "value_display": card_obj.value_display
    }
