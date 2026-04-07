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
        self.pixmaps: list[QPixmap] = []
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
        self.pixmaps = [pm for pm in (left, right) if not pm.isNull()]
        self.update()

    def set_pixmap_list(self, pixmaps: list[QPixmap]) -> None:
        self.pixmaps = [pm for pm in pixmaps if not pm.isNull()]
        if self.pixmaps:
            self.left_pixmap = self.pixmaps[0]
        if len(self.pixmaps) > 1:
            self.right_pixmap = self.pixmaps[1]
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.mode == "grid" and self.pixmaps:
            painter = QPainter(self)
            target = self.rect()
            cols = 2 if len(self.pixmaps) > 1 else 1
            rows = (len(self.pixmaps) + cols - 1) // cols
            cell_w = max(1, target.width() // cols)
            cell_h = max(1, target.height() // max(1, rows))
            for index, pm in enumerate(self.pixmaps):
                row = index // cols
                col = index % cols
                cell = target.adjusted(col * cell_w, row * cell_h, -(target.width() - (col + 1) * cell_w), -(target.height() - (row + 1) * cell_h))
                scaled = pm.scaled(cell.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = cell.x() + (cell.width() - scaled.width()) // 2
                y = cell.y() + (cell.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            painter.end()
            return
        if self.left_pixmap.isNull():
            return
        painter = QPainter(self)
        target = self.rect()
        if self.right_pixmap.isNull():
            pixmap = self.left_pixmap.scaled(target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (target.width() - pixmap.width()) // 2
            y = (target.height() - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
        else:
            left_target = target.adjusted(0, 0, -target.width() // 2, 0)
            right_target = target.adjusted(target.width() // 2, 0, 0, 0)
            left = self.left_pixmap.scaled(left_target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            right = self.right_pixmap.scaled(right_target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(left_target.x() + (left_target.width() - left.width()) // 2, left_target.y() + (left_target.height() - left.height()) // 2, left)
            painter.drawPixmap(right_target.x() + (right_target.width() - right.width()) // 2, right_target.y() + (right_target.height() - right.height()) // 2, right)
        painter.end()
