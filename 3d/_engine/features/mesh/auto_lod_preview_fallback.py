from __future__ import annotations

import math

from .auto_lod_inspect import PreviewMesh
from .auto_lod_viewport_state import ViewportState, fit_view, reset_view

try:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen, QPolygonF, QWheelEvent
    from PySide6.QtWidgets import QFrame, QSizePolicy
except ImportError as exc:
    raise ImportError("PySide6 is required for the Auto LOD fallback preview viewport.") from exc


class FallbackMeshViewport(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(320)
        self.setMaximumHeight(720)
        self._mesh: PreviewMesh | None = None
        self._message = "Preview fallback"
        self._viewport_state = ViewportState()
        self._last_pos: QPointF | None = None
        self._drag_mode = "orbit"

    def set_preview_mesh(self, mesh: PreviewMesh | None, message: str) -> None:
        self._mesh = mesh
        self._message = message
        self.update()

    def set_wireframe(self, enabled: bool) -> None:
        self._viewport_state.wireframe = enabled
        self.update()

    def reset_camera(self) -> None:
        reset_view(self._viewport_state)
        self.update()

    def fit_camera(self) -> None:
        fit_view(self._viewport_state)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() in {Qt.LeftButton, Qt.RightButton}:
            self._last_pos = event.position()
            self._drag_mode = "pan" if event.button() == Qt.RightButton or bool(event.modifiers() & Qt.ShiftModifier) else "orbit"
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._last_pos is None:
            super().mouseMoveEvent(event)
            return
        delta = event.position() - self._last_pos
        self._last_pos = event.position()
        if self._drag_mode == "pan":
            width = max(1.0, float(self.width()))
            height = max(1.0, float(self.height()))
            self._viewport_state.pan_x += delta.x() / width * 2.2
            self._viewport_state.pan_y -= delta.y() / height * 2.2
        else:
            self._viewport_state.yaw_degrees += delta.x() * 0.6
            self._viewport_state.pitch_degrees = max(-89.0, min(89.0, self._viewport_state.pitch_degrees + delta.y() * 0.5))
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._last_pos = None
        self._drag_mode = "orbit"
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta:
            factor = 0.88 if delta > 0 else 1.12
            self._viewport_state.distance_scale = max(1.2, min(10.0, self._viewport_state.distance_scale * factor))
            self.update()
            event.accept()
            return
        super().wheelEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#12171d"))
        self._draw_grid(painter)
        if self._mesh is None:
            painter.setPen(QPen(QColor("#a7b0ba"), 1))
            painter.drawText(self.rect().adjusted(24, 24, -24, -24), Qt.AlignCenter, self._message)
            return
        for depth, polygon in self._project_faces():
            fill = QColor("#8ed9ff")
            fill.setAlpha(max(65, min(210, int(190 - depth * 16))))
            if self._viewport_state.wireframe:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor("#d8f6ff"), 1.2))
            else:
                painter.setBrush(fill)
                painter.setPen(QPen(QColor("#d8f6ff"), 0.9))
            painter.drawPolygon(polygon)

    def _draw_grid(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        width = self.width()
        height = self.height()
        step = max(48, min(width, height) // 8)
        for x in range(step, width, step):
            painter.drawLine(x, 0, x, height)
        for y in range(step, height, step):
            painter.drawLine(0, y, width, y)

    def _rotate(self, point: tuple[float, float, float]) -> tuple[float, float, float]:
        yaw = math.radians(self._viewport_state.yaw_degrees)
        pitch = math.radians(self._viewport_state.pitch_degrees)
        x, y, z = point
        cos_yaw = math.cos(yaw)
        sin_yaw = math.sin(yaw)
        rx = x * cos_yaw + z * sin_yaw
        rz = -x * sin_yaw + z * cos_yaw
        cos_pitch = math.cos(pitch)
        sin_pitch = math.sin(pitch)
        ry = y * cos_pitch - rz * sin_pitch
        rz2 = y * sin_pitch + rz * cos_pitch
        return rx, ry, rz2

    def _project_faces(self) -> list[tuple[float, QPolygonF]]:
        if self._mesh is None:
            return []
        bounds = self._mesh.bounds
        cx, cy, cz = bounds.center
        radius = max(bounds.radius, 0.5)
        scale = min(self.width(), self.height()) / (radius * self._viewport_state.distance_scale * 2.0)
        projected: list[tuple[float, QPolygonF]] = []
        for a, b, c in self._mesh.faces:
            points = []
            avg_depth = 0.0
            for index in (a, b, c):
                vx, vy, vz = self._mesh.vertices[index]
                rx, ry, rz = self._rotate((vx - cx, vy - cy, vz - cz))
                avg_depth += rz
                sx = self.width() / 2 + (rx + self._viewport_state.pan_x * radius) * scale
                sy = self.height() / 2 - (ry + self._viewport_state.pan_y * radius) * scale
                points.append(QPointF(sx, sy))
            projected.append((avg_depth / 3.0, QPolygonF(points)))
        projected.sort(key=lambda item: item[0], reverse=True)
        return projected
