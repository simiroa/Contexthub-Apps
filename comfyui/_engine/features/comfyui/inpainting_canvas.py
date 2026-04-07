"""Inpainting brush canvas widget.

QGraphicsView-based interactive canvas for painting inpainting masks
over source images. Supports brush / eraser modes, undo / redo,
zoom / pan, and exports the mask as a PIL Image.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
    QMouseEvent,
    QKeyEvent,
)
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QGraphicsPixmapItem,
)


_MASK_COLOR = QColor(255, 60, 60, 120)   # semi-transparent red overlay
_ERASE_COLOR = QColor(0, 0, 0, 0)        # fully transparent = erase

_MAX_UNDO = 40


class InpaintingCanvas(QGraphicsView):
    """Interactive canvas for painting inpainting masks."""

    mask_changed = Signal()           # emitted after each stroke completes
    image_loaded = Signal(str)        # emitted when a new image is set (path)
    zoom_changed = Signal(float)      # current zoom factor

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Image layer
        self._image_item: Optional[QGraphicsPixmapItem] = None
        self._source_pixmap: Optional[QPixmap] = None

        # Mask layer (painted on an off-screen QImage)
        self._mask_image: Optional[QImage] = None
        self._mask_item: Optional[QGraphicsPixmapItem] = None

        # Brush state
        self._brush_size: int = 30
        self._eraser_mode: bool = False
        self._painting: bool = False
        self._last_point: Optional[QPointF] = None

        # Undo stack
        self._undo_stack: list[QImage] = []
        self._redo_stack: list[QImage] = []

        # Panning state
        self._panning: bool = False
        self._pan_start = QPointF()

        # Zoom
        self._zoom_factor: float = 1.0

        # View setup
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("border: none; background: transparent;")
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_image(self, path: str | Path) -> bool:
        """Load an image as the canvas source. Returns True on success."""
        path = Path(path)
        if not path.exists():
            return False
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return False

        self._source_pixmap = pixmap
        self._scene.clear()
        self._image_item = self._scene.addPixmap(pixmap)
        self._image_item.setZValue(0)

        # Create blank mask
        self._mask_image = QImage(pixmap.size(), QImage.Format.Format_ARGB32_Premultiplied)
        self._mask_image.fill(QColor(0, 0, 0, 0))
        self._mask_item = self._scene.addPixmap(QPixmap.fromImage(self._mask_image))
        self._mask_item.setZValue(1)

        # Reset view
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._zoom_factor = 1.0
        self.resetTransform()
        self.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self._image_item, Qt.AspectRatioMode.KeepAspectRatio)

        self.image_loaded.emit(str(path))
        return True

    def clear_mask(self) -> None:
        """Erase the entire mask."""
        if self._mask_image is None:
            return
        self._push_undo()
        self._mask_image.fill(QColor(0, 0, 0, 0))
        self._refresh_mask()
        self.mask_changed.emit()

    def get_mask_qimage(self) -> Optional[QImage]:
        """Return the mask as a black-and-white QImage (white = inpaint area)."""
        if self._mask_image is None:
            return None
        w, h = self._mask_image.width(), self._mask_image.height()
        bw = QImage(w, h, QImage.Format.Format_Grayscale8)
        bw.fill(QColor(0, 0, 0))
        for y in range(h):
            for x in range(w):
                alpha = QColor(self._mask_image.pixel(x, y)).alpha()
                if alpha > 10:
                    bw.setPixelColor(x, y, QColor(255, 255, 255))
        return bw

    def get_mask_pil(self):
        """Return the mask as a Pillow grayscale Image, or None."""
        try:
            from PIL import Image
        except ImportError:
            return None
        qimg = self.get_mask_qimage()
        if qimg is None:
            return None
        w, h = qimg.width(), qimg.height()
        # Convert to bytes quickly
        ptr = qimg.bits()
        if ptr is None:
            return None
        arr = bytes(ptr)
        return Image.frombytes("L", (w, h), arr)

    def has_image(self) -> bool:
        return self._source_pixmap is not None and not self._source_pixmap.isNull()

    def has_mask(self) -> bool:
        """Check if any mask pixels are painted."""
        if self._mask_image is None:
            return False
        for y in range(self._mask_image.height()):
            for x in range(self._mask_image.width()):
                if QColor(self._mask_image.pixel(x, y)).alpha() > 10:
                    return True
        return False

    @property
    def brush_size(self) -> int:
        return self._brush_size

    @brush_size.setter
    def brush_size(self, value: int) -> None:
        self._brush_size = max(2, min(200, value))

    @property
    def eraser_mode(self) -> bool:
        return self._eraser_mode

    @eraser_mode.setter
    def eraser_mode(self, value: bool) -> None:
        self._eraser_mode = value

    def undo(self) -> None:
        if not self._undo_stack or self._mask_image is None:
            return
        self._redo_stack.append(self._mask_image.copy())
        self._mask_image = self._undo_stack.pop()
        self._refresh_mask()
        self.mask_changed.emit()

    def redo(self) -> None:
        if not self._redo_stack or self._mask_image is None:
            return
        self._undo_stack.append(self._mask_image.copy())
        self._mask_image = self._redo_stack.pop()
        self._refresh_mask()
        self.mask_changed.emit()

    def fit_view(self) -> None:
        if self._image_item:
            self.fitInView(self._image_item, Qt.AspectRatioMode.KeepAspectRatio)

    # ------------------------------------------------------------------
    # Mouse events – painting and panning
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Middle button → pan
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        # Left button → paint/erase
        if event.button() == Qt.MouseButton.LeftButton and self._mask_image is not None:
            self._push_undo()
            self._painting = True
            scene_pos = self.mapToScene(event.position().toPoint())
            self._paint_at(scene_pos)
            self._last_point = scene_pos
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            return

        if self._painting and self._mask_image is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            if self._last_point is not None:
                self._paint_line(self._last_point, scene_pos)
            else:
                self._paint_at(scene_pos)
            self._last_point = scene_pos
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton and self._painting:
            self._painting = False
            self._last_point = None
            self.mask_changed.emit()
            return

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        # Ctrl+Wheel → zoom, plain wheel → brush size
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self._zoom_factor *= factor
            self.scale(factor, factor)
            self.zoom_changed.emit(self._zoom_factor)
        else:
            delta = 2 if event.angleDelta().y() > 0 else -2
            self.brush_size = self._brush_size + delta

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.redo()
                else:
                    self.undo()
                return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Internal painting primitives
    # ------------------------------------------------------------------

    def _paint_at(self, pos: QPointF) -> None:
        painter = QPainter(self._mask_image)
        if self._eraser_mode:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 0))
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_MASK_COLOR)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawEllipse(pos, self._brush_size / 2, self._brush_size / 2)
        painter.end()
        self._refresh_mask()

    def _paint_line(self, p1: QPointF, p2: QPointF) -> None:
        painter = QPainter(self._mask_image)
        if self._eraser_mode:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pen = QPen(QColor(0, 0, 0, 0), self._brush_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(_MASK_COLOR, self._brush_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        self._refresh_mask()

    def _refresh_mask(self) -> None:
        if self._mask_item is not None and self._mask_image is not None:
            self._mask_item.setPixmap(QPixmap.fromImage(self._mask_image))

    def _push_undo(self) -> None:
        if self._mask_image is None:
            return
        self._undo_stack.append(self._mask_image.copy())
        if len(self._undo_stack) > _MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
