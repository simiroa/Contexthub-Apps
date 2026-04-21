from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from shared._engine.components.icon_button import build_icon_button


class ToggleButtonStrip(QWidget):
    """
    Horizontal strip of toggle buttons for selecting a mode or option.
    Uses unified styling with primary/secondary contrast boundaries.
    """
    valueChanged = Signal(str)

    # Standard styling tokens for segmented controls
    STYLE_ACTIVE = "background-color: #3b82f6; color: white; border-radius: 4px; font-weight: bold; border: none;"
    STYLE_INACTIVE = "background-color: #2d3748; color: #a0aec0; border-radius: 4px; border: 1px solid transparent;"
    HEIGHT_STD = 24

    def __init__(self, options: list[str], current_value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 2, 0, 8)
        self.layout.setSpacing(4)

        self.buttons = {}
        for opt in options:
            btn = build_icon_button(opt, role="secondary" if opt != current_value else "primary")
            btn.setFixedHeight(self.HEIGHT_STD)
            btn.setCheckable(True)
            btn.setChecked(opt == current_value)
            
            # Application of abstract token styling
            self._apply_button_style(btn, opt == current_value)
                
            btn.clicked.connect(lambda _, val=opt: self._on_clicked(val))
            self.layout.addWidget(btn)
            self.buttons[opt] = btn

    def _on_clicked(self, value: str) -> None:
        for opt, btn in self.buttons.items():
            is_active = (opt == value)
            btn.setChecked(is_active)
            self._apply_button_style(btn, is_active)
        self.valueChanged.emit(value)

    def _apply_button_style(self, btn: QPushButton, is_active: bool) -> None:
        btn.setStyleSheet(self.STYLE_ACTIVE if is_active else self.STYLE_INACTIVE)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
