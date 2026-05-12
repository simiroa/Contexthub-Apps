from __future__ import annotations
import math
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, Slot
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor, QPen, QBrush, QTransform
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsItem, QFrame, QVBoxLayout, QWidget, QGraphicsRectItem, QGraphicsObject
)

class SplitSliderItem(QGraphicsObject):
    """
    A vertical line that acts as a divider for split-screen comparison.
    """
    position_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.SizeHorCursor)
        self._ratio = 0.5
        self._view_width = 800
        self._z_value = 1000

    def set_view_width(self, width: float):
        self._view_width = width
        self._update_pos_from_ratio()

    def set_ratio(self, ratio: float):
        self._ratio = max(0.0, min(1.0, ratio))
        self._update_pos_from_ratio()

    def ratio(self) -> float:
        return self._ratio

    def _update_pos_from_ratio(self):
        self.setPos(self._view_width * self._ratio, 0)

    def boundingRect(self) -> QRectF:
        # A thin interaction handle
        return QRectF(-10, -5000, 20, 10000)

    def paint(self, painter: QPainter, option, widget):
        # Draw a sleek line
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Subtle glow
        glow_pen = QPen(QColor(0, 150, 255, 60), 6)
        painter.setPen(glow_pen)
        painter.drawLine(0, -5000, 0, 5000)

        # Core line
        line_pen = QPen(QColor(255, 255, 255, 220), 2)
        painter.setPen(line_pen)
        painter.drawLine(0, -5000, 0, 5000)

        # Handle Circle
        painter.setBrush(QColor(0, 120, 212))
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(-8, -8, 16, 16)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            # Constrain to view width
            x = max(0.0, min(self._view_width, new_pos.x()))
            self._ratio = x / self._view_width if self._view_width > 0 else 0.5
            self.position_changed.emit(self._ratio)
            return QPointF(x, 0)
        return super().itemChange(change, value)

class DiffVisualizationItem(QGraphicsPixmapItem):
    """Renders difference heatmap with semi-transparent blending."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.alpha_blend = 0.6

    def paint(self, painter: QPainter, option, widget):
        if self.pixmap().isNull():
            return
        painter.save()
        painter.setOpacity(self.alpha_blend)
        super().paint(painter, option, widget)
        painter.restore()

class DedicatedCompareView(QGraphicsView):
    """
    High-performance QGraphicsView for image comparison.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        # Background
        self.setBackgroundBrush(QBrush(QColor(18, 18, 18)))

        # State
        self.mode = "split"

        # Create items with correct types from initialization
        self.slider = SplitSliderItem()
        self.img_item_a = ClippingPixmapItem("left", self.slider)
        self.img_item_b = ClippingPixmapItem("right", self.slider)
        self.diff_item = DiffVisualizationItem()

        self.scene.addItem(self.img_item_a)
        self.scene.addItem(self.img_item_b)
        self.scene.addItem(self.diff_item)
        self.scene.addItem(self.slider)

        # Z-order: slider on top, B on top for clip-side, diff in middle
        self.img_item_a.setZValue(10)
        self.img_item_b.setZValue(11)
        self.diff_item.setZValue(12)
        self.slider.setZValue(100)

        # Initial Zoom
        self._zoom = 1.0

    def set_mode(self, mode: str):
        self.mode = mode
        self.update_layout()

    def set_pixmaps(self, pixmaps: list[QPixmap]):
        if not pixmaps:
            self.img_item_a.setPixmap(QPixmap())
            self.img_item_b.setPixmap(QPixmap())
            self.diff_item.setPixmap(QPixmap())
            return

        self.img_item_a.setPixmap(pixmaps[0])
        if len(pixmaps) > 1:
            self.img_item_b.setPixmap(pixmaps[1])
            # Align B to A
            self.img_item_b.setPos(0, 0)
        else:
            self.img_item_b.setPixmap(QPixmap())

        # Set diff pixmap if provided (index 2)
        if len(pixmaps) > 2:
            self.diff_item.setPixmap(pixmaps[2])
        else:
            self.diff_item.setPixmap(QPixmap())

        self.update_layout()
        if self.mode == "grid":
            self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        elif not self.img_item_a.pixmap().isNull():
            self.fitInView(self.img_item_a, Qt.KeepAspectRatio)

    def update_layout(self):
        if self.mode == "split":
            self.img_item_a.setVisible(True)
            self.img_item_b.setVisible(True)
            self.img_item_b.setPos(0, 0)  # reset after grid mode
            self.slider.setVisible(True)
            self.diff_item.setVisible(False)
        elif self.mode == "grid":
            self.slider.setVisible(False)
            self.img_item_a.setVisible(True)
            self.img_item_b.setVisible(True)
            self.diff_item.setVisible(False)
            if not self.img_item_a.pixmap().isNull():
                w_a = self.img_item_a.pixmap().width()
                self.img_item_b.setPos(w_a + 20, 0)
        elif self.mode == "single":
            self.slider.setVisible(False)
            self.img_item_a.setVisible(True)
            self.img_item_b.setVisible(False)
            self.diff_item.setVisible(False)
        elif self.mode == "diff":
            self.slider.setVisible(False)
            self.img_item_a.setVisible(True)
            self.img_item_b.setVisible(False)  # B hidden; A is the base
            self.diff_item.setVisible(True)
            self.diff_item.setPos(0, 0)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)

class ClippingPixmapItem(QGraphicsPixmapItem):
    def __init__(self, side="left", slider_target=None):
        super().__init__()
        self.side = side
        self.slider = slider_target

    def paint(self, painter: QPainter, option, widget):
        if not self.slider or not self.slider.isVisible():
            super().paint(painter, option, widget)
            return

        # Get local clip
        slider_x_in_scene = self.slider.pos().x()
        # Map scene slider x to local item coordinates
        local_slider_x = self.mapFromScene(QPointF(slider_x_in_scene, 0)).x()
        
        painter.save()
        if self.side == "left":
            rect = self.boundingRect()
            rect.setRight(local_slider_x)
            painter.setClipRect(rect)
        else:
            rect = self.boundingRect()
            rect.setLeft(local_slider_x)
            painter.setClipRect(rect)
            
        super().paint(painter, option, widget)
        painter.restore()

class AdvancedCompareWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.view = DedicatedCompareView()
        self.layout.addWidget(self.view)
        self._current_pixmap_width = 0

    def set_mode(self, mode: str):
        self.view.set_mode(mode)
        # In split mode, ensure slider covers the Union bounding rect
        if mode == "split":
            rect = self.view.img_item_a.pixmap().rect()
            if not rect.isEmpty():
                self.view.slider.set_view_width(rect.width())
                self.view.slider.setPos(rect.width() * 0.5, 0)

    def set_pixmap_list(self, pixmaps: list[QPixmap]):
        self.view.set_pixmaps(pixmaps)
        # Update slider constraints
        if pixmaps and pixmaps[0]:
            self._current_pixmap_width = pixmaps[0].width()
            if self.view.mode == "split":
                self.view.slider.set_view_width(pixmaps[0].width())
                self.view.slider.setPos(pixmaps[0].width() * 0.5, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.view.mode == "split" and self._current_pixmap_width > 0:
            self.view.slider.set_view_width(self._current_pixmap_width)
