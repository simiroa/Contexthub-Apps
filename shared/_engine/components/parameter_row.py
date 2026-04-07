from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
)

from contexthub.ui.qt.shell import get_shell_metrics


class ParameterRow(QWidget):
    """
    Standardized Parameter Row for Contexthub-Apps.
    Ensures a consistent Label (Eyebrow) + Field layout with proper spacing and 26px alignment.
    """
    
    def __init__(self, label_text: str, field: QWidget, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.m = get_shell_metrics()
        self._init_ui(label_text, field)

    def _init_ui(self, label_text: str, field: QWidget):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label (Eyebrow)
        self.label = QLabel(label_text.upper())
        self.label.setObjectName("eyebrow")
        self.label.setFixedWidth(60) # Consistent eyebrow width
        
        # Field (any compact field)
        self.field = field
        
        layout.addWidget(self.label)
        layout.addWidget(self.field, 1)
        self.setFixedHeight(self.m.input_min_height)
