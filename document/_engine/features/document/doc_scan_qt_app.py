from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    get_shell_palette,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
)
from features.document.doc_scan_commands import (
    CornerAdjustCommand,
    GrayscaleToggleCommand,
    ResetCornersCommand,
    RotateImageCommand,
    SignaturePositionCommand,
    SignatureScaleCommand,
)
from features.document.doc_scan_service import DocScanService
from features.document.doc_scan_state import DocScanState

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, QPointF, QRectF, Signal, QUrl
    from PySide6.QtGui import QColor, QImage, QPainter, QPen, QBrush, QPixmap, QKeySequence, QShortcut, QUndoStack
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
        QSlider,
    )
    from shared._engine.components.icon_button import build_icon_button
except ImportError as exc:
    raise ImportError("PySide6 is required for doc_scan.") from exc

import cv2
import numpy as np

APP_ID = "doc_scan"
APP_TITLE = qt_t("doc_scan.title", "Document Scanner")
APP_SUBTITLE = qt_t("doc_scan.subtitle", "Adjust corners and export a perspective-corrected image.")

HANDLE_RADIUS = 10
HIT_RADIUS = 20
IMG_PADDING = 0.08

BLEND_MODES = [
    ("multiply", qt_t("doc_scan.blend_multiply", "Multiply (white → transparent)")),
    ("darken", qt_t("doc_scan.blend_darken", "Darken")),
    ("normal", qt_t("doc_scan.blend_normal", "Normal")),
]

_TAB_STYLE = (
    "QPushButton { background: transparent; border: none; border-bottom: 2px solid transparent; "
    "font-weight: 600; padding: 6px 16px; color: #999; }"
    "QPushButton:checked { border-bottom: 2px solid #4a9eff; color: white; }"
    "QPushButton:disabled { color: #555; }"
)


def _cv_to_pixmap(image: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w, c = rgb.shape
    q_img = QImage(rgb.data, w, h, c * w, QImage.Format_RGB888)
    return QPixmap.fromImage(q_img)


class SignaturePanel(QFrame):
    """Collapsible right-side panel for signature settings."""
    signature_loaded = Signal()
    signature_changed = Signal()
    reset_position_requested = Signal()

    def __init__(self, state: DocScanState, service: DocScanService) -> None:
        super().__init__()
        self.state = state
        self.service = service
        self.setObjectName("card")
        self.setFixedWidth(256)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel(qt_t("doc_scan.signature", "Signature"))
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        load_btn = build_icon_button(
            qt_t("doc_scan.load_signature", "Load PNG"),
            icon_name="upload", role="secondary",
        )
        load_btn.clicked.connect(self._on_load)
        layout.addWidget(load_btn)

        self.filename_label = QLabel("")
        self.filename_label.setStyleSheet("color: #aaa; font-size: 9px;")
        self.filename_label.setWordWrap(True)
        layout.addWidget(self.filename_label)

        hint = QLabel(qt_t("doc_scan.signature_hint", "Drag to move · corner to resize"))
        hint.setStyleSheet("color: #666; font-size: 9px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(self._sep())

        layout.addWidget(QLabel(qt_t("doc_scan.blend_mode", "Blend Mode")))
        self.blend_combo = QComboBox()
        for key, label in BLEND_MODES:
            self.blend_combo.addItem(label, key)
        self._select_blend(self.state.signature_blend_mode)
        self.blend_combo.currentIndexChanged.connect(self._on_blend_changed)
        layout.addWidget(self.blend_combo)

        layout.addWidget(QLabel(qt_t("doc_scan.signature_opacity", "Opacity")))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(int(self.state.signature_opacity))
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(25)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        layout.addWidget(self.opacity_slider)

        self.opacity_label = QLabel(f"{int(self.state.signature_opacity)}%")
        self.opacity_label.setStyleSheet("color: #aaa; font-size: 9px;")
        self.opacity_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.opacity_label)

        layout.addWidget(self._sep())

        reset_btn = build_icon_button(
            qt_t("doc_scan.signature_reset", "Reset Position"),
            icon_name="refresh-cw", role="secondary",
        )
        reset_btn.clicked.connect(self.reset_position_requested.emit)
        layout.addWidget(reset_btn)

        layout.addStretch()

    def _sep(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #333;")
        return line

    def _select_blend(self, key: str) -> None:
        for i in range(self.blend_combo.count()):
            if self.blend_combo.itemData(i) == key:
                self.blend_combo.blockSignals(True)
                self.blend_combo.setCurrentIndex(i)
                self.blend_combo.blockSignals(False)
                return

    def sync_from_state(self) -> None:
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(int(self.state.signature_opacity))
        self.opacity_slider.blockSignals(False)
        self.opacity_label.setText(f"{int(self.state.signature_opacity)}%")
        self._select_blend(self.state.signature_blend_mode)
        self.filename_label.setText(
            self.state.signature_path.name if self.state.signature_path else ""
        )

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None, qt_t("doc_scan.load_signature_title", "Load Signature PNG"),
            "", "PNG Images (*.png)",
        )
        if path and self.service.load_signature(path):
            self.filename_label.setText(Path(path).name)
            self.signature_loaded.emit()

    def _on_blend_changed(self) -> None:
        self.state.signature_blend_mode = self.blend_combo.currentData()
        self.signature_changed.emit()

    def _on_opacity_changed(self) -> None:
        self.state.signature_opacity = self.opacity_slider.value()
        self.opacity_label.setText(f"{self.state.signature_opacity}%")
        self.signature_changed.emit()


class ScanView(QWidget):
    corners_changed = Signal()
    corner_adjustment_finished = Signal(int, tuple, tuple)
    signature_position_finished = Signal(tuple, tuple)
    signature_scale_finished = Signal(float, float)
    signature_changed = Signal()
    image_dropped = Signal(str)
    open_image_requested = Signal()

    def __init__(self, state: DocScanState, service: DocScanService) -> None:
        super().__init__()
        self.state = state
        self.service = service
        self.mode = "edit"
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 300)
        self.setAcceptDrops(True)

        self._active = -1
        self._corner_start: Optional[Tuple[float, float]] = None
        self._sig_active = False
        self._sig_resize_active = False
        self._sig_start_pos: Optional[Tuple[float, float]] = None
        self._sig_start_scale: Optional[float] = None
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._pan_active = False
        self._pan_start_mouse: Optional[QPointF] = None
        self._pan_start_val: Optional[QPointF] = None

    def reset_zoom(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self.update()

    # ── geometry helpers ───────────────────────────────────────────────────────

    def _img_rect(self) -> QRectF:
        if self.state.image is None:
            return QRectF()
        h, w = self.state.image.shape[:2]
        sw, sh = self.width(), self.height()
        avail_w = sw * (1.0 - IMG_PADDING * 2)
        avail_h = sh * (1.0 - IMG_PADDING * 2)
        ratio = min(avail_w / w, avail_h / h)
        rw, rh = w * ratio, h * ratio
        if self.mode == "preview":
            cx = sw / 2 + self._pan.x()
            cy = sh / 2 + self._pan.y()
            nw, nh = rw * self._zoom, rh * self._zoom
            return QRectF(cx - nw / 2, cy - nh / 2, nw, nh)
        return QRectF((sw - rw) / 2, (sh - rh) / 2, rw, rh)

    def _to_screen(self, nx: float, ny: float, r: QRectF) -> QPointF:
        return QPointF(r.x() + nx * r.width(), r.y() + ny * r.height())

    def _to_norm(self, sx: float, sy: float, r: QRectF) -> Tuple[float, float]:
        return (
            max(0.0, min(1.0, (sx - r.x()) / r.width())),
            max(0.0, min(1.0, (sy - r.y()) / r.height())),
        )

    def _sig_screen_rect(self, r: QRectF) -> Optional[QRectF]:
        if self.state.signature_image is None:
            return None
        sig_h, sig_w = self.state.signature_image.shape[:2]
        if sig_w <= 0 or sig_h <= 0:
            return None
        sw = r.width() * self.state.signature_scale
        sh = sig_h * sw / sig_w
        cx = r.x() + self.state.signature_x * r.width()
        cy = r.y() + self.state.signature_y * r.height()
        return QRectF(cx - sw / 2, cy - sh / 2, sw, sh)

    def _sig_handles(self, sr: QRectF) -> List[QPointF]:
        return [sr.topLeft(), sr.topRight(), sr.bottomLeft(), sr.bottomRight()]

    # ── painting ───────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = get_shell_palette()
        painter.fillRect(self.rect(), QColor(palette.field_bg))

        if self.state.image is None:
            painter.setPen(QColor(getattr(palette, "muted_text", "#888")))
            h1 = qt_t("doc_scan.open_hint", "Click or drop an image")
            h2 = qt_t("doc_scan.open_hint_sub", "(Ctrl+O)")
            painter.drawText(self.rect(), Qt.AlignCenter, f"{h1}\n\n{h2}")
            return

        rect = self._img_rect()
        if self.mode == "edit":
            self._draw_edit_border(painter)
            self._paint_edit(painter, rect, palette)
        else:
            self._paint_preview(painter, rect, palette)

    def _draw_edit_border(self, painter: QPainter) -> None:
        pen = QPen(QColor(100, 150, 255, 100), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(1, 1, self.width() - 2, self.height() - 2))

    def _paint_edit(self, painter: QPainter, rect: QRectF, palette) -> None:
        painter.drawPixmap(rect.toRect(), _cv_to_pixmap(self.state.image))

        corners = self.state.corners
        pts = [self._to_screen(c[0], c[1], rect) for c in corners]

        accent = QColor(palette.accent)
        accent.setAlpha(180)
        painter.setPen(QPen(accent, 2))
        painter.setBrush(Qt.NoBrush)
        for i in range(4):
            painter.drawLine(pts[i], pts[(i + 1) % 4])

        for i, pt in enumerate(pts):
            fill = QColor(palette.accent)
            fill.setAlpha(255 if i == self._active else 200)
            painter.setBrush(QBrush(fill))
            painter.setPen(QPen(QColor("white"), 2))
            painter.drawEllipse(pt, HANDLE_RADIUS, HANDLE_RADIUS)

    def _paint_preview(self, painter: QPainter, rect: QRectF, palette) -> None:
        warped = self.service.get_warped()
        if warped is None:
            return
        with_sig = self.service._overlay_signature(warped)
        painter.drawPixmap(rect.toRect(), _cv_to_pixmap(with_sig))

        sr = self._sig_screen_rect(rect)
        if sr is None:
            return
        accent = QColor(palette.accent)
        outline = QColor(accent)
        outline.setAlpha(180)
        painter.setPen(QPen(outline, 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(sr)

        handle_fill = QColor(accent)
        handle_fill.setAlpha(220)
        painter.setBrush(QBrush(handle_fill))
        painter.setPen(QPen(QColor("white"), 1))
        for corner in self._sig_handles(sr):
            painter.drawRect(QRectF(corner.x() - 5, corner.y() - 5, 10, 10))

    # ── events ─────────────────────────────────────────────────────────────────

    def wheelEvent(self, event) -> None:
        if self.mode != "preview" or self.state.image is None:
            return
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else (1.0 / 1.15)
        old_zoom = self._zoom
        new_zoom = max(0.25, min(10.0, self._zoom * factor))
        if abs(new_zoom - old_zoom) < 1e-6:
            event.accept()
            return
        pos = event.position()
        sw, sh = self.width(), self.height()
        center = QPointF(sw / 2.0, sh / 2.0)
        r = new_zoom / old_zoom
        self._pan = (pos - center) * (1.0 - r) + self._pan * r
        self._zoom = new_zoom
        self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if self.mode == "preview" and event.button() == Qt.LeftButton and self.state.image is not None:
            self.reset_zoom()

    def mousePressEvent(self, event) -> None:
        if self.state.image is None:
            if event.button() == Qt.LeftButton:
                self.open_image_requested.emit()
            return

        if event.button() == Qt.MiddleButton and self.mode == "preview":
            self._pan_active = True
            self._pan_start_mouse = event.position()
            self._pan_start_val = QPointF(self._pan)
            return

        rect = self._img_rect()
        pos = event.position()

        if self.mode == "edit":
            for i, c in enumerate(self.state.corners):
                pt = self._to_screen(c[0], c[1], rect)
                if (pos - pt).manhattanLength() < HIT_RADIUS:
                    self._active = i
                    self._corner_start = c
                    self.update()
                    return
            self._active = -1

        elif self.mode == "preview" and self.state.signature_image is not None:
            sr = self._sig_screen_rect(rect)
            if sr is None:
                return
            for corner in self._sig_handles(sr):
                if (pos - corner).manhattanLength() < 14:
                    self._sig_resize_active = True
                    self._sig_start_scale = self.state.signature_scale
                    return
            if sr.contains(pos):
                self._sig_active = True
                self._sig_start_pos = (self.state.signature_x, self.state.signature_y)

    def mouseMoveEvent(self, event) -> None:
        if self._pan_active and self._pan_start_mouse is not None:
            self._pan = self._pan_start_val + (event.position() - self._pan_start_mouse)
            self.update()
            return

        rect = self._img_rect()
        pos = event.position()

        if self.mode == "edit" and self._active >= 0 and self.state.image is not None:
            self.state.corners[self._active] = self._to_norm(pos.x(), pos.y(), rect)
            self.update()
            self.corners_changed.emit()

        elif self.mode == "preview" and self.state.signature_image is not None:
            if self._sig_resize_active:
                cx = rect.x() + self.state.signature_x * rect.width()
                cy = rect.y() + self.state.signature_y * rect.height()
                sig = self.state.signature_image
                sig_h, sig_w = sig.shape[:2]
                if sig_w <= 0 or sig_h <= 0 or rect.width() <= 0:
                    return
                aspect = sig_h / sig_w
                dx = abs(pos.x() - cx)
                dy = abs(pos.y() - cy)
                new_w = 2 * max(dx, dy / max(aspect, 1e-6))
                self.state.signature_scale = max(0.05, min(1.5, new_w / rect.width()))
                self.update()
                self.signature_changed.emit()
            elif self._sig_active:
                norm = self._to_norm(pos.x(), pos.y(), rect)
                self.state.signature_x = norm[0]
                self.state.signature_y = norm[1]
                self.update()
                self.signature_changed.emit()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._pan_active = False
            self._pan_start_mouse = None
            self._pan_start_val = None
            return

        if self._active >= 0 and self._corner_start is not None:
            new_pos = self.state.corners[self._active]
            if new_pos != self._corner_start:
                self.corner_adjustment_finished.emit(self._active, self._corner_start, new_pos)
            self._corner_start = None

        if self._sig_active and self._sig_start_pos is not None:
            new_pos = (self.state.signature_x, self.state.signature_y)
            if new_pos != self._sig_start_pos:
                self.signature_position_finished.emit(self._sig_start_pos, new_pos)
            self._sig_start_pos = None

        if self._sig_resize_active and self._sig_start_scale is not None:
            new_scale = self.state.signature_scale
            if new_scale != self._sig_start_scale:
                self.signature_scale_finished.emit(self._sig_start_scale, new_scale)
            self._sig_start_scale = None

        self._active = -1
        self._sig_active = False
        self._sig_resize_active = False
        self.update()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            if paths:
                self.image_dropped.emit(paths[0])
            event.acceptProposedAction()


class DocScanWindow(QMainWindow):
    def __init__(self, state: DocScanState, service: DocScanService, app_root: Path) -> None:
        super().__init__()
        self.state = state
        self.service = service
        self.app_root = app_root
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_sig = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime)
        self._notify_timer = QTimer(self)
        self._notify_timer.setSingleShot(True)
        self._notify_timer.timeout.connect(self._clear_notification)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1100, 800)
        self.setMinimumSize(600, 500)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._undo_stack = QUndoStack(self)

        self._build_ui()
        self._restore_geometry()
        self._bind()
        self._refresh()
        self._runtime_timer.start()

    # ── layout ─────────────────────────────────────────────────────────────────

    def _vline(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #444;")
        sep.setFixedWidth(1)
        return sep

    def _build_ui(self) -> None:
        m = get_shell_metrics()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell = QVBoxLayout(self.window_shell)
        shell.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell.setSpacing(m.section_gap)

        # Header
        self.header = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        self.header.open_webui_btn.hide()
        self.header.set_header_visibility(
            show_subtitle=False, show_asset_count=False, show_runtime_status=False
        )
        shell.addWidget(self.header)

        # Global action bar
        global_bar = QHBoxLayout()
        global_bar.setContentsMargins(0, 0, 0, 0)
        global_bar.setSpacing(8)

        self.open_btn = build_icon_button(
            qt_t("doc_scan.open", "Open Image"), icon_name="folder-open", role="secondary"
        )
        global_bar.addWidget(self.open_btn)
        global_bar.addWidget(self._vline())

        self.undo_btn = build_icon_button(
            qt_t("doc_scan.undo", "Undo"), icon_name="undo-2", role="secondary"
        )
        self.redo_btn = build_icon_button(
            qt_t("doc_scan.redo", "Redo"), icon_name="redo-2", role="secondary"
        )
        self.undo_btn.setEnabled(False)
        self.redo_btn.setEnabled(False)
        global_bar.addWidget(self.undo_btn)
        global_bar.addWidget(self.redo_btn)
        global_bar.addStretch(1)

        self.sig_toggle_btn = build_icon_button(
            qt_t("doc_scan.signature", "Signature"), icon_name="pen-line", role="secondary"
        )
        self.sig_toggle_btn.setCheckable(True)
        self.sig_toggle_btn.setEnabled(False)
        global_bar.addWidget(self.sig_toggle_btn)
        global_bar.addWidget(self._vline())

        self.export_btn = build_icon_button(
            qt_t("doc_scan.export", "Export PNG"), icon_name="download", role="primary"
        )
        self.export_btn.setEnabled(False)
        global_bar.addWidget(self.export_btn)
        shell.addLayout(global_bar)

        # Mode tabs (centered)
        tab_row = QHBoxLayout()
        tab_row.setContentsMargins(0, 0, 0, 0)
        tab_row.setSpacing(0)
        tab_row.addStretch()

        self.edit_btn = QPushButton(qt_t("doc_scan.edit", "Edit"))
        self.preview_btn = QPushButton(qt_t("doc_scan.preview", "Preview"))
        for btn in (self.edit_btn, self.preview_btn):
            btn.setFixedSize(80, 32)
            btn.setCheckable(True)
            btn.setEnabled(False)
            btn.setStyleSheet(_TAB_STYLE)
        tab_row.addWidget(self.edit_btn)
        tab_row.addWidget(self.preview_btn)
        tab_row.addStretch()
        shell.addLayout(tab_row)

        # Edit toolbar (shown only in edit mode)
        self.edit_toolbar = QFrame()
        edit_bar = QHBoxLayout(self.edit_toolbar)
        edit_bar.setContentsMargins(0, 0, 0, 0)
        edit_bar.setSpacing(8)

        self.reset_btn = build_icon_button(
            qt_t("doc_scan.reset", "Reset Corners"), icon_name="refresh-cw", role="secondary"
        )
        self.rotate_ccw_btn = build_icon_button(
            qt_t("doc_scan.rotate_ccw", "Rotate CCW"), icon_name="rotate-ccw", role="secondary"
        )
        self.rotate_cw_btn = build_icon_button(
            qt_t("doc_scan.rotate_cw", "Rotate CW"), icon_name="rotate-cw", role="secondary"
        )
        self.grayscale_btn = build_icon_button(
            qt_t("doc_scan.grayscale", "Grayscale"), icon_name="palette", role="secondary"
        )
        self.grayscale_btn.setCheckable(True)

        for btn in (self.reset_btn, self.rotate_ccw_btn, self.rotate_cw_btn, self.grayscale_btn):
            edit_bar.addWidget(btn)
            btn.setEnabled(False)
        edit_bar.addStretch()
        shell.addWidget(self.edit_toolbar)

        # Preview toolbar (shown only in preview mode)
        self.preview_toolbar = QFrame()
        prev_bar = QHBoxLayout(self.preview_toolbar)
        prev_bar.setContentsMargins(0, 0, 0, 0)
        prev_bar.setSpacing(6)

        self.fit_btn = build_icon_button(
            qt_t("doc_scan.fit", "Fit"), icon_name="maximize", role="secondary"
        )
        self.zoom_minus_btn = build_icon_button("−", role="secondary")
        self.zoom_minus_btn.setFixedWidth(36)
        self.zoom_display = QLabel("100%")
        self.zoom_display.setAlignment(Qt.AlignCenter)
        self.zoom_display.setFixedWidth(52)
        self.zoom_display.setStyleSheet("color: #ccc; font-size: 12px;")
        self.zoom_plus_btn = build_icon_button("+", role="secondary")
        self.zoom_plus_btn.setFixedWidth(36)

        for w in (self.fit_btn, self.zoom_minus_btn, self.zoom_display, self.zoom_plus_btn):
            prev_bar.addWidget(w)
        prev_bar.addStretch()
        self.preview_toolbar.hide()
        shell.addWidget(self.preview_toolbar)

        # Content area: viewport + optional signature side panel
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(8)

        viewport_card = QFrame()
        viewport_card.setObjectName("card")
        vp_layout = QVBoxLayout(viewport_card)
        vp_layout.setContentsMargins(0, 0, 0, 0)
        vp_layout.setSpacing(0)

        self.scan_view = ScanView(self.state, self.service)
        vp_layout.addWidget(self.scan_view)
        content.addWidget(viewport_card, 1)

        self.sig_panel = SignaturePanel(self.state, self.service)
        self.sig_panel.hide()
        content.addWidget(self.sig_panel)

        shell.addLayout(content, 1)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 10px; padding: 2px 0;")
        shell.addWidget(self.status_label)

        self.size_grip = attach_size_grip(shell, self.window_shell)
        root.addWidget(self.window_shell)

    # ── bindings ───────────────────────────────────────────────────────────────

    def _bind(self) -> None:
        self._undo_stack.canUndoChanged.connect(self.undo_btn.setEnabled)
        self._undo_stack.canRedoChanged.connect(self.redo_btn.setEnabled)
        self._undo_stack.indexChanged.connect(self._on_undo_redo)
        self.undo_btn.clicked.connect(self._undo_stack.undo)
        self.redo_btn.clicked.connect(self._undo_stack.redo)

        self.open_btn.clicked.connect(self._on_open)
        self.export_btn.clicked.connect(self._on_export)
        self.edit_btn.clicked.connect(lambda: self._set_mode("edit"))
        self.preview_btn.clicked.connect(lambda: self._set_mode("preview"))
        self.reset_btn.clicked.connect(self._on_reset)
        self.rotate_cw_btn.clicked.connect(self._on_rotate_cw)
        self.rotate_ccw_btn.clicked.connect(self._on_rotate_ccw)
        self.grayscale_btn.clicked.connect(self._on_grayscale)
        self.fit_btn.clicked.connect(self._on_zoom_fit)
        self.zoom_minus_btn.clicked.connect(self._on_zoom_minus)
        self.zoom_plus_btn.clicked.connect(self._on_zoom_plus)
        self.sig_toggle_btn.clicked.connect(self._on_sig_toggle)

        self.scan_view.image_dropped.connect(self._on_image_dropped)
        self.scan_view.open_image_requested.connect(self._on_open)
        self.scan_view.corner_adjustment_finished.connect(self._on_corner_adjusted)
        self.scan_view.signature_position_finished.connect(self._on_sig_moved)
        self.scan_view.signature_scale_finished.connect(self._on_sig_scaled)
        self.scan_view.signature_changed.connect(self.sig_panel.sync_from_state)
        self.sig_panel.signature_changed.connect(self.scan_view.update)
        self.sig_panel.signature_loaded.connect(self._on_signature_loaded)
        self.sig_panel.reset_position_requested.connect(self._on_sig_reset_pos)

        QShortcut(QKeySequence.Undo, self).activated.connect(self._undo_stack.undo)
        QShortcut(QKeySequence.Redo, self).activated.connect(self._undo_stack.redo)
        QShortcut(QKeySequence.Open, self).activated.connect(self._on_open)
        QShortcut(QKeySequence.Save, self).activated.connect(self._on_export)
        QShortcut(QKeySequence("E"), self).activated.connect(lambda: self._set_mode("edit"))
        QShortcut(QKeySequence("P"), self).activated.connect(lambda: self._set_mode("preview"))
        QShortcut(QKeySequence("R"), self).activated.connect(self._on_rotate_cw)
        QShortcut(QKeySequence("Shift+R"), self).activated.connect(self._on_rotate_ccw)
        QShortcut(QKeySequence("G"), self).activated.connect(self._on_grayscale)
        QShortcut(QKeySequence("S"), self).activated.connect(self._on_sig_toggle_shortcut)
        QShortcut(QKeySequence("0"), self).activated.connect(self._on_zoom_fit)
        QShortcut(QKeySequence("Plus"), self).activated.connect(self._on_zoom_plus)
        QShortcut(QKeySequence("Minus"), self).activated.connect(self._on_zoom_minus)

    # ── mode switching ─────────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        self.scan_view.mode = mode
        self.edit_btn.setChecked(mode == "edit")
        self.preview_btn.setChecked(mode == "preview")
        self.edit_toolbar.setVisible(mode == "edit")
        self.preview_toolbar.setVisible(mode == "preview")
        self._refresh()

    # ── state refresh ──────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        has_image = self.state.image is not None

        self.edit_btn.setEnabled(has_image)
        self.preview_btn.setEnabled(has_image)
        self.export_btn.setEnabled(has_image)
        self.sig_toggle_btn.setEnabled(has_image)

        self.reset_btn.setEnabled(has_image)
        self.rotate_ccw_btn.setEnabled(has_image)
        self.rotate_cw_btn.setEnabled(has_image)
        self.grayscale_btn.setEnabled(has_image)
        self.grayscale_btn.setChecked(self.state.is_grayscale)

        self.fit_btn.setEnabled(has_image)
        self.zoom_minus_btn.setEnabled(has_image)
        self.zoom_plus_btn.setEnabled(has_image)

        if has_image:
            name = self.state.image_path.name if self.state.image_path else "Unknown"
            h, w = self.state.image.shape[:2]
            self.status_label.setText(f"{name}  ·  {w} × {h} px")
        else:
            self.status_label.setText("")

        self._update_zoom_display()
        self.scan_view.update()

    def _update_zoom_display(self) -> None:
        self.zoom_display.setText(f"{int(round(self.scan_view._zoom * 100))}%")

    # ── action handlers ────────────────────────────────────────────────────────

    def _on_undo_redo(self) -> None:
        self._refresh()
        self.sig_panel.sync_from_state()
        self.scan_view.update()

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, qt_t("doc_scan.open_title", "Open Image"), "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if path and self.service.load_image(path):
            self.scan_view.reset_zoom()
            self._set_mode("edit")

    def _on_image_dropped(self, path: str) -> None:
        if self.service.load_image(path):
            self.scan_view.reset_zoom()
            self._set_mode("edit")

    def _on_export(self) -> None:
        if self.state.image is None:
            return
        stem = self.state.image_path.stem if self.state.image_path else "scanned"
        default_dir = str(self.state.image_path.parent) if self.state.image_path else ""
        path, _ = QFileDialog.getSaveFileName(
            self, qt_t("doc_scan.export_title", "Export PNG"),
            str(Path(default_dir) / f"{stem}_scanned.png"),
            "PNG Image (*.png)",
        )
        if not path:
            return
        if self.service.save_png(path):
            self._show_notification(f"✓ Saved: {Path(path).name}")
            msg = QMessageBox(self)
            msg.setWindowTitle(APP_TITLE)
            msg.setText(qt_t("doc_scan.saved", f"Saved:\n{path}"))
            msg.addButton(qt_t("doc_scan.open_folder", "Open Folder"), QMessageBox.AcceptRole)
            msg.addButton(QMessageBox.Close)
            if msg.exec() == 0:
                os.startfile(str(Path(path).parent))

    def _on_reset(self) -> None:
        if self.state.image is None:
            return
        old_corners = self.state.corners.copy()
        self._undo_stack.push(ResetCornersCommand(self.service, old_corners))
        self.scan_view.update()

    def _on_rotate_cw(self) -> None:
        if self.state.image is not None:
            self._undo_stack.push(RotateImageCommand(self.service, clockwise=True))
            self._refresh()

    def _on_rotate_ccw(self) -> None:
        if self.state.image is not None:
            self._undo_stack.push(RotateImageCommand(self.service, clockwise=False))
            self._refresh()

    def _on_grayscale(self) -> None:
        self._undo_stack.push(GrayscaleToggleCommand(self.service))
        self._refresh()

    def _on_sig_toggle(self) -> None:
        self.sig_panel.setVisible(self.sig_toggle_btn.isChecked())

    def _on_sig_toggle_shortcut(self) -> None:
        self.sig_toggle_btn.setChecked(not self.sig_toggle_btn.isChecked())
        self._on_sig_toggle()

    def _on_signature_loaded(self) -> None:
        if self.state.image is not None:
            self._set_mode("preview")
        if not self.sig_panel.isVisible():
            self.sig_toggle_btn.setChecked(True)
            self.sig_panel.setVisible(True)
        self.sig_panel.sync_from_state()
        self.scan_view.update()

    def _on_corner_adjusted(self, idx: int, old: tuple, new: tuple) -> None:
        self._undo_stack.push(CornerAdjustCommand(self.state, idx, old, new))

    def _on_sig_moved(self, old_pos: tuple, new_pos: tuple) -> None:
        self._undo_stack.push(SignaturePositionCommand(
            self.state, old_pos[0], old_pos[1], new_pos[0], new_pos[1]
        ))
        self.sig_panel.sync_from_state()

    def _on_sig_scaled(self, old_scale: float, new_scale: float) -> None:
        self._undo_stack.push(SignatureScaleCommand(self.state, old_scale, new_scale))
        self.sig_panel.sync_from_state()

    def _on_sig_reset_pos(self) -> None:
        old_x, old_y = self.state.signature_x, self.state.signature_y
        new_x, new_y = 0.7, 0.85
        if (old_x, old_y) != (new_x, new_y):
            self._undo_stack.push(SignaturePositionCommand(self.state, old_x, old_y, new_x, new_y))
        self.scan_view.update()

    # ── zoom ───────────────────────────────────────────────────────────────────

    def _on_zoom_minus(self) -> None:
        if self.state.image is not None:
            self.scan_view._zoom = max(0.25, self.scan_view._zoom / 1.2)
            self.scan_view.update()
            self._update_zoom_display()

    def _on_zoom_plus(self) -> None:
        if self.state.image is not None:
            self.scan_view._zoom = min(10.0, self.scan_view._zoom * 1.2)
            self.scan_view.update()
            self._update_zoom_display()

    def _on_zoom_fit(self) -> None:
        self.scan_view.reset_zoom()
        self._update_zoom_display()

    # ── notifications ──────────────────────────────────────────────────────────

    def _show_notification(self, text: str) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: #4f4; font-size: 10px; padding: 2px 0; font-weight: bold;")
        self._notify_timer.start(2500)

    def _clear_notification(self) -> None:
        self.status_label.setStyleSheet("color: #888; font-size: 10px; padding: 2px 0;")
        self._refresh()

    # ── runtime / geometry ─────────────────────────────────────────────────────

    def _check_runtime(self) -> None:
        sig = runtime_settings_signature()
        if sig != self._runtime_sig:
            self._runtime_sig = sig
            refresh_runtime_preferences()
            self.setStyleSheet(build_shell_stylesheet())

    def _restore_geometry(self) -> None:
        geom = self._settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        if self._settings.value("is_maximized", False, bool):
            self.showMaximized()

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    state = DocScanState()
    service = DocScanService(state)
    if targets:
        service.load_targets(targets)
    app_root = Path(__file__).resolve().parents[3] / "document" / "doc_scan"
    window = DocScanWindow(state, service, app_root)
    window.show()
    return app.exec()
