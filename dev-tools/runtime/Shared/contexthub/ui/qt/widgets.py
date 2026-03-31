from __future__ import annotations

from pathlib import Path

from .theme_metrics import get_shell_metrics
from .theme_palette import get_shell_palette

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QFontMetrics, QPainter, QColor
    from PySide6.QtWidgets import QFrame, QLabel, QListWidget, QSizeGrip, QWidget
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt shell runtime.") from exc


class CollapsibleSection(QFrame):
    def __init__(self, title: str, expanded: bool = True):
        super().__init__()
        self.setObjectName("card")
        self._expanded = expanded
        self._body_visible = expanded

        layout = self.layout()
        if layout is None:
            from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QToolButton

            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(8)

            header = QHBoxLayout()
            header.setContentsMargins(0, 0, 0, 0)
            header.setSpacing(8)
            self.title_label = QLabel(title)
            self.title_label.setObjectName("sectionTitle")
            header.addWidget(self.title_label, 1)

            self.toggle_btn = QToolButton()
            self.toggle_btn.setObjectName("windowChrome")
            self.toggle_btn.clicked.connect(self._toggle_expanded)
            header.addWidget(self.toggle_btn, 0, Qt.AlignRight)
            layout.addLayout(header)

            self.body = QWidget()
            self.body_layout = QVBoxLayout(self.body)
            self.body_layout.setContentsMargins(0, 0, 0, 0)
            self.body_layout.setSpacing(8)
            layout.addWidget(self.body)
        self.set_expanded(expanded)

    def _toggle_expanded(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._body_visible = expanded
        self.body.setVisible(expanded)
        self.toggle_btn.setText("−" if expanded else "+")

    def add_widget(self, widget: QWidget) -> None:
        self.body_layout.addWidget(widget)

    def finish(self) -> None:
        self.set_expanded(self._expanded)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setWordWrap(False)
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full_text = text or ""
        super().setText(self._full_text)
        self.setToolTip(self._full_text if self._full_text else "")
        self._apply_elision()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_elision()

    def full_text(self) -> str:
        return self._full_text

    def _apply_elision(self) -> None:
        if not self._full_text:
            super().setText("")
            return
        width = max(0, self.contentsRect().width())
        if width <= 0:
            super().setText(self._full_text)
            return
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(self._full_text, Qt.ElideRight, width))


class VisibleSizeGrip(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.SizeFDiagCursor)
        self._grip = QSizeGrip(self)
        self._grip.setStyleSheet("background: transparent;")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._grip.setGeometry(self.rect())

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        color = QColor(get_shell_palette().text_muted)
        color.setAlpha(140)
        painter.setPen(color)
        edge = self.width() - 3
        painter.drawLine(edge - 8, edge, edge, edge - 8)
        painter.drawLine(edge - 12, edge, edge, edge - 12)
        painter.drawLine(edge - 16, edge, edge, edge - 16)
        painter.end()


class DropListWidget(QListWidget):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)
