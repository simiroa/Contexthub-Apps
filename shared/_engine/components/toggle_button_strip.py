from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget

from shared._engine.components.icon_button import build_icon_button


class ToggleButtonStrip(QWidget):
    """
    Horizontal strip of toggle buttons for selecting a mode or option.
    Uses unified styling with primary/secondary contrast boundaries.
    """
    valueChanged = Signal(str)

    HEIGHT_STD = 24

    def __init__(self, options: list[str], current_value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 2, 0, 8)
        self.layout.setSpacing(4)

        self.buttons = {}
        for opt in options:
            btn = build_icon_button(opt, role="segment")
            btn.setFixedHeight(self.HEIGHT_STD)
            btn.setCheckable(True)
            btn.setChecked(opt == current_value)
                
            btn.clicked.connect(lambda _, val=opt: self._on_clicked(val))
            self.layout.addWidget(btn)
            self.buttons[opt] = btn

    def _on_clicked(self, value: str) -> None:
        for opt, btn in self.buttons.items():
            btn.setChecked(opt == value)
        self.valueChanged.emit(value)
