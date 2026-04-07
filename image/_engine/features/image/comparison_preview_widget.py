from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPixmap, QPainter, QBrush, QColor
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
)

class ComparisonPreviewWidget(QGraphicsView):
    """
    Immersive image preview with zoom, pan, and click-to-compare.
    Optimized for pixel-perfect detail comparison by scaling original layer 
    to match the result (upscaled) dimensions exactly.
    """
    dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setBackgroundBrush(QBrush(QColor(22, 24, 28)))

        # Rounded edges and clear border
        self.setObjectName("previewView")
        self.setStyleSheet("""
            #previewView {
                border: 2px solid #3f4e64;
                border-radius: 12px;
                background-color: #16181c;
            }
        """)
        
        # Layers
        self.original_item = QGraphicsPixmapItem()
        self.result_item = QGraphicsPixmapItem()
        
        # High-quality scaling for comparison
        self.original_item.setTransformationMode(Qt.SmoothTransformation)
        self.result_item.setTransformationMode(Qt.SmoothTransformation)
        
        self.scene.addItem(self.original_item)
        self.scene.addItem(self.result_item)
        
        self.original_pixmap = QPixmap()
        self.result_pixmap = QPixmap()

        self._is_comparing = False
        self._overlay_label = QLabel("Drop Image to Start", self)
        self._overlay_label.setAlignment(Qt.AlignCenter)
        self._overlay_label.setStyleSheet("color: #4a5568; font-weight: bold; background: transparent; font-size: 14px;")

    def set_pixmaps(self, original: QPixmap, result: QPixmap | None = None) -> None:
        self.original_pixmap = original
        self.result_pixmap = result or original
        
        # 1. Update Pixmaps
        self.original_item.setPixmap(self.original_pixmap)
        self.result_item.setPixmap(self.result_pixmap)
        
        # 2. Pixel-Perfect Spatial Matching
        # Scale original scene item to match result's pixel boundary exactly
        if not self.result_pixmap.isNull() and not self.original_pixmap.isNull():
            rw, rh = self.result_pixmap.width(), self.result_pixmap.height()
            ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
            if ow > 0 and oh > 0:
                # Reset scale first to prevent accumulation
                self.original_item.setScale(1.0)
                self.original_item.setScale(rw / ow)
                
        # 3. Z-Order (Result B on top)
        self.result_item.setZValue(10)
        self.original_item.setZValue(5)
        
        self._overlay_label.setVisible(self.original_pixmap.isNull())
        
        # 4. Update Scene Rect to match result
        if not self.result_pixmap.isNull():
            self.setSceneRect(self.result_item.boundingRect())
            
    def show_original(self, show: bool) -> None:
        self._is_comparing = show
        self.result_item.setVisible(not show)
        # Keep original visible underneath for instant flip
        self.original_item.setVisible(True)

    def wheelEvent(self, event) -> None:
        if self.original_pixmap.isNull(): return
        factor = 1.15 if event.angleDelta().y() > 0 else 1/1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and not self.original_pixmap.isNull():
            self.show_original(True)
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.show_original(False)
            self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.dropped.emit(files)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._overlay_label.resize(self.size())

    def fit_image(self) -> None:
        if not self.result_pixmap.isNull():
            self.fitInView(self.result_item, Qt.KeepAspectRatio)
