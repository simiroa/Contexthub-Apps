from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QWidget,
)

from contexthub.ui.qt.shell import get_shell_metrics

class VerticalParameterRow(QWidget):
    """
    Standardized Vertical Parameter Row for Contexthub-Apps.
    Ensures a consistent Label (Eyebrow) + Field stacking layout with proper 10px bold eyebrow font.
    """
    def __init__(self, label_text: str, field: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.m = get_shell_metrics()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 8)
        layout.setSpacing(6)
        
        self.label = QLabel(label_text.upper())
        self.label.setObjectName("eyebrow")
        self.label.setStyleSheet("font-size: 10px; opacity: 0.8; font-weight: bold; color: #8892b0;")
        
        self.field = field
        layout.addWidget(self.label)
        layout.addWidget(self.field)
