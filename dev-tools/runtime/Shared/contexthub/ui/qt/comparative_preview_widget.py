from __future__ import annotations

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtWidgets import QLabel
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


class ComparativePreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.left_pixmap = QPixmap()
        self.right_pixmap = QPixmap()
        self.mode = "single"
        self.split_ratio = 0.5
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(220)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def set_pixmaps(self, left: QPixmap, right: QPixmap) -> None:
        self.left_pixmap = left
        self.right_pixmap = right
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.left_pixmap.isNull():
            return
        painter = QPainter(self)
        target = self.rect()
        pixmap = self.left_pixmap.scaled(target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (target.width() - pixmap.width()) // 2
        y = (target.height() - pixmap.height()) // 2
        painter.drawPixmap(x, y, pixmap)
        painter.end()
