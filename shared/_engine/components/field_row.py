from __future__ import annotations

from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from contexthub.ui.qt.shell import get_shell_metrics


class LabeledFieldRow(QWidget):
    def __init__(
        self,
        label_text: str,
        field: QWidget,
        *,
        orientation: str = "horizontal",
        label_width: int | None = None,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
        spacing: int = 8,
        fixed_height: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.m = get_shell_metrics()
        self.label = QLabel(label_text.upper())
        self.label.setObjectName("eyebrow")
        self.field = field
        self.layout = self._build_layout(
            orientation,
            margins=margins,
            spacing=spacing,
            label_width=label_width,
        )
        if fixed_height is not None:
            self.setFixedHeight(fixed_height)

    def _build_layout(
        self,
        orientation: str,
        *,
        margins: tuple[int, int, int, int],
        spacing: int,
        label_width: int | None,
    ) -> QBoxLayout:
        if orientation == "vertical":
            layout: QBoxLayout = QVBoxLayout(self)
            layout.addWidget(self.label)
            layout.addWidget(self.field)
        else:
            layout = QHBoxLayout(self)
            if label_width is not None:
                self.label.setFixedWidth(label_width)
            layout.addWidget(self.label)
            layout.addWidget(self.field, 1)
        layout.setContentsMargins(*margins)
        layout.setSpacing(spacing)
        return layout
