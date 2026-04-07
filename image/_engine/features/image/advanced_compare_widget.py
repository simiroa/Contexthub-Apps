from __future__ import annotations
import math
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, Slot
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor, QPen, QBrush, QTransform
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
    QGraphicsItem, QFrame, QVBoxLayout, QWidget, QGraphicsRectItem
)

class SplitSliderItem(QGraphicsItem):
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
            return QPointF(x, 0)
        return super().itemChange(change, value)

class DedicatedCompareView(QGraphicsView):
    """
    High-performance QGraphicsView for image comparison.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Rendering hints for quality
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setOptimizationFlags(QGraphicsView.IndirectPainting)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Background
        self.setBackgroundBrush(QBrush(QColor(18, 18, 18)))
        
        # State
        self.mode = "split"
        self.img_item_a = QGraphicsPixmapItem()
        self.img_item_b = QGraphicsPixmapItem()
        self.scene.addItem(self.img_item_a)
        self.scene.addItem(self.img_item_b)
        
        # Split Slider
        self.slider = SplitSliderItem()
        self.scene.addItem(self.slider)
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
            return

        self.img_item_a.setPixmap(pixmaps[0])
        if len(pixmaps) > 1:
            self.img_item_b.setPixmap(pixmaps[1])
            # Align B to A
            self.img_item_b.setPos(0, 0)
        else:
            self.img_item_b.setPixmap(QPixmap())
        
        self.update_layout()
        self.fitInView(self.img_item_a, Qt.KeepAspectRatio)

    def update_layout(self):
        if self.mode == "split":
            self.img_item_a.setVisible(True)
            self.img_item_b.setVisible(True)
            self.slider.setVisible(True)
            # Clip logic will be handled in paintEvent or via Shader-like approach
            # For simplicity in pure Python/Qt, we use ClipPath in a custom Item
            # but here we'll use a wrapper or the viewport's paint overrider.
        elif self.mode == "grid":
            self.slider.setVisible(False)
            self.img_item_a.setVisible(True)
            self.img_item_b.setVisible(True)
            # Side by side
            w_a = self.img_item_a.pixmap().width()
            self.img_item_b.setPos(w_a + 20, 0)
        elif self.mode == "single":
            self.slider.setVisible(False)
            self.img_item_a.setVisible(True)
            self.img_item_b.setVisible(False)
        elif self.mode == "diff":
            self.slider.setVisible(False)
            self.img_item_a.setVisible(True)
            self.img_item_b.setVisible(True)
            # We would need a custom shader or pixel-manipulated image for diff
            # For now, let's just stack them.
            self.img_item_b.setPos(0, 0)
        
        self.scene.update()

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """
        Handle the split-screen clipping effect.
        """
        if self.mode != "split" or self.img_item_b.pixmap().isNull():
            return super().drawForeground(painter, rect)

        # Get slider position in scene coordinates
        slider_x = self.slider.pos().x()
        
        # We want to draw img_item_a for x < slider_x 
        # and img_item_b for x > slider_x
        # But QGraphicsScene draws items in Z order.
        # To achieve "Wipe", we can clip the top item.
        
        # Actually, it's easier to override the paint of the items, 
        # but for a quick fix, let's use the painter's clip.
        # But drawForeground is called after items.
        
        # Better approach: AdvancedCompareWidget handles the clipping 
        # by overriding paint in a custom QGraphicsPixmapItem.
        pass

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
        
        # Replace items with clipping ones
        self.view.scene.removeItem(self.view.img_item_a)
        self.view.scene.removeItem(self.view.img_item_b)
        
        self.view.img_item_a = ClippingPixmapItem("left", self.view.slider)
        self.view.img_item_b = ClippingPixmapItem("right", self.view.slider)
        
        self.view.scene.addItem(self.view.img_item_a)
        self.view.scene.addItem(self.view.img_item_b)
        self.view.img_item_a.setZValue(10)
        self.view.img_item_b.setZValue(11) # B on top clip-side

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
        if self.view.mode == "split" and pixmaps:
            self.view.slider.set_view_width(pixmaps[0].width())
            self.view.slider.setPos(pixmaps[0].width() * 0.5, 0)
