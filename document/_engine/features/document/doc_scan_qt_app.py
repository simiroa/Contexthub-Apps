from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

from contexthub.ui.qt.panels import FixedParameterPanel
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
from features.document.doc_scan_service import DocScanService
from features.document.doc_scan_state import DocScanState

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, QPointF, QRectF, Signal
    from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QPushButton,
        QRadioButton,
        QButtonGroup,
        QSplitter,
        QVBoxLayout,
        QWidget,
        QMessageBox,
        QSizePolicy,
        QFileDialog,
        QSlider,
    )
    from shared._engine.components.icon_button import build_icon_button
except ImportError as exc:
    raise ImportError("PySide6 is required for doc_scan.") from exc

import cv2
import numpy as np

APP_ID = "doc_scan"
APP_TITLE = qt_t("doc_scan.title", "Document Scanner")
APP_SUBTITLE = qt_t("doc_scan.subtitle", "Scan, rotate, unwarp, and sign documents.")


class InteractivePreview(QWidget):
    """Custom widget to handle corner dragging and signature placement."""
    changed = Signal()

    def __init__(self, state: DocScanState, service: DocScanService) -> None:
        super().__init__()
        self.state = state
        self.service = service
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(400, 400)
        
        self.pixmap: Optional[QPixmap] = None
        self.active_handle = -1  # 0-3 for corners, 10 for signature
        self.handle_size = 12

    def set_image(self, pixmap: QPixmap) -> None:
        self.pixmap = pixmap
        self.update()

    def _get_pixmap_rect(self) -> QRectF:
        if not self.pixmap:
            return QRectF()
        
        w, h = self.pixmap.width(), self.pixmap.height()
        sw, sh = self.width(), self.height()
        
        ratio = min(sw / w, sh / h)
        rw, rh = w * ratio, h * ratio
        rx, ry = (sw - rw) / 2, (sh - rh) / 2
        
        return QRectF(rx, ry, rw, rh)

    def _map_to_ui(self, norm_pt: Tuple[float, float], rect: QRectF) -> QPointF:
        return QPointF(rect.x() + norm_pt[0] * rect.width(), rect.y() + norm_pt[1] * rect.height())

    def _map_from_ui(self, ui_pt: QPointF, rect: QRectF) -> Tuple[float, float]:
        nx = (ui_pt.x() - rect.x()) / rect.width()
        ny = (ui_pt.y() - rect.y()) / rect.height()
        return (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))

    def paintEvent(self, event) -> None: # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = get_shell_palette()

        # Background
        painter.fillRect(self.rect(), QColor(palette.field_bg))

        rect = self._get_pixmap_rect()
        if self.pixmap:
            painter.drawPixmap(rect.toRect(), self.pixmap)
            
        if self.state.current_index < 0:
            return
            
        item = self.state.items[self.state.current_index]
        
        # Draw Unwarp Handles if unwarp is NOT active (editing mode)
        if not item.unwarp_active and item.corners:
            accent = QColor(palette.accent)
            painter.setPen(QPen(accent, 2))
            pts = [self._map_to_ui(c, rect) for c in item.corners]
            
            # Connect corners
            painter.drawLine(pts[0], pts[1])
            painter.drawLine(pts[1], pts[2])
            painter.drawLine(pts[2], pts[3])
            painter.drawLine(pts[3], pts[0])
            
            # Draw Handles
            for i, p in enumerate(pts):
                handle_color = QColor(accent if self.active_handle == i else accent)
                if self.active_handle != i:
                    handle_color.setAlpha(100)
                painter.setBrush(QBrush(handle_color))
                painter.drawEllipse(p, self.handle_size/2, self.handle_size/2)

        # Draw Signature Overlay Handle
        if self.state.signature_image is not None and item.signature_pos:
            sig_pt = self._map_to_ui(item.signature_pos, rect)
            painter.setPen(QPen(Qt.white, 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 255, 255, 100) if self.active_handle == 10 else Qt.transparent))
            
            # Estimate signature box in UI
            sw = rect.width() * item.signature_scale
            sh = sw * (self.state.signature_image.shape[0] / self.state.signature_image.shape[1])
            painter.drawRect(QRectF(sig_pt.x() - sw/2, sig_pt.y() - sh/2, sw, sh))
            painter.drawEllipse(sig_pt, 6, 6)

    def mousePressEvent(self, event) -> None: # noqa: N802
        if self.state.current_index < 0: return
        item = self.state.items[self.state.current_index]
        rect = self._get_pixmap_rect()
        pos = event.position()
        
        # Check Signature handle first (top level)
        if self.state.signature_image is not None and item.signature_pos:
            sig_pt = self._map_to_ui(item.signature_pos, rect)
            if (pos - sig_pt).manhattanLength() < 20:
                self.active_handle = 10
                self.update()
                return
        
        # Check Corners (only if unwarp not active)
        if not item.unwarp_active and item.corners:
            for i, c in enumerate(item.corners):
                ui_pt = self._map_to_ui(c, rect)
                if (pos - ui_pt).manhattanLength() < 15:
                    self.active_handle = i
                    self.update()
                    return
                    
        self.active_handle = -1

    def mouseMoveEvent(self, event) -> None: # noqa: N802
        if self.active_handle == -1: return
        
        item = self.state.items[self.state.current_index]
        rect = self._get_pixmap_rect()
        norm_pos = self._map_from_ui(event.position(), rect)
        
        if self.active_handle == 10:
            item.signature_pos = norm_pos
        elif 0 <= self.active_handle < 4:
            item.corners[self.active_handle] = norm_pos
            
        self.update()
        self.changed.emit()

    def mouseReleaseEvent(self, event) -> None: # noqa: N802
        self.active_handle = -1
        self.update()


class DocScanWindow(QMainWindow):
    def __init__(self, state: DocScanState, app_root: str | Path) -> None:
        super().__init__()
        self.state = state
        self.service = DocScanService(state)
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1280, 800)
        self.setMinimumSize(1000, 700)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        self._refresh_all()
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        m = get_shell_metrics()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(m.section_gap)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        self.header_surface.open_webui_btn.hide()
        self.header_surface.set_header_visibility(
            show_subtitle=False,
            show_asset_count=True,
            show_runtime_status=False,
        )
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        
        # --- Left Panel: Pages ---
        self.pages_card = QFrame()
        self.pages_card.setObjectName("card")
        pages_layout = QVBoxLayout(self.pages_card)
        pages_layout.setContentsMargins(12, 12, 12, 12)
        pages_layout.setSpacing(8)
        
        pages_title = QLabel(qt_t("doc_scan.pages", "Pages"))
        pages_title.setObjectName("sectionTitle")
        self.page_list = QListWidget()
        self.page_list.setObjectName("inputList")
        
        pages_layout.addWidget(pages_title)
        pages_layout.addWidget(self.page_list, 1)
        
        # --- Center Panel: Preview ---
        self.preview_card = QFrame()
        self.preview_card.setObjectName("subtlePanel")
        preview_layout = QVBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(4, 4, 4, 4)
        
        self.interactive_preview = InteractivePreview(self.state, self.service)
        preview_layout.addWidget(self.interactive_preview)
        
        # --- Right Panel: Tools ---
        self.tools_card = QFrame()
        self.tools_card.setObjectName("card")
        tools_layout = QVBoxLayout(self.tools_card)
        tools_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        tools_layout.setSpacing(m.section_gap)
        
        self.param_panel = FixedParameterPanel(
            title=qt_t("doc_scan.tools", "Tools"),
            description=qt_t("doc_scan.tools_desc", "Adjust layout and appearance."),
        )
        self.param_panel.preset_label.hide()
        self.param_panel.preset_combo.hide()
        
        # Section 1: Page Layout
        layout_box = QFrame()
        layout_box_layout = QVBoxLayout(layout_box)
        layout_box_layout.setContentsMargins(0, 0, 0, 0)
        
        rot_row = QHBoxLayout()
        rot_row.setSpacing(8)
        self.rot_left_btn = build_icon_button(qt_t("doc_scan.rot_left", "Left"), icon_name="rotate-ccw", role="secondary")
        self.rot_right_btn = build_icon_button(qt_t("doc_scan.rot_right", "Right"), icon_name="rotate-cw", role="secondary")
        rot_row.addWidget(self.rot_left_btn)
        rot_row.addWidget(self.rot_right_btn)
        
        self.unwarp_btn = build_icon_button(qt_t("doc_scan.unwarp", "Unwarp (ON/OFF)"), icon_name="maximize", role="secondary")
        self.unwarp_btn.setCheckable(True)
        
        layout_box_layout.addLayout(rot_row)
        layout_box_layout.addWidget(self.unwarp_btn)
        
        self.param_panel.add_field(qt_t("doc_scan.page_layout", "Page Layout"), layout_box)

        # Section 2: Visibility Filter
        filter_group_box = QFrame()
        filter_group_layout = QVBoxLayout(filter_group_box)
        filter_group_layout.setContentsMargins(0, 0, 0, 0)
        
        self.filter_group = QButtonGroup(self)
        self.radio_orig = QRadioButton(qt_t("doc_scan.filter_orig", "Original"))
        self.radio_bw = QRadioButton(qt_t("doc_scan.filter_bw", "B&W Document"))
        self.radio_magic = QRadioButton(qt_t("doc_scan.filter_magic", "Magic Color"))
        
        self.filter_group.addButton(self.radio_orig, 0)
        self.filter_group.addButton(self.radio_bw, 1)
        self.filter_group.addButton(self.radio_magic, 2)
        
        filter_group_layout.addWidget(self.radio_orig)
        filter_group_layout.addWidget(self.radio_bw)
        filter_group_layout.addWidget(self.radio_magic)
        
        self.param_panel.add_field(qt_t("doc_scan.filter", "Document Filter"), filter_group_box)

        # Section 3: Signature
        self.sig_box = QFrame()
        sig_layout = QVBoxLayout(self.sig_box)
        sig_layout.setContentsMargins(0, 0, 0, 0)
        sig_layout.setSpacing(8)
        
        self.load_sig_btn = build_icon_button(qt_t("doc_scan.load_sig", "Load Marker (PNG)"), icon_name="pen-tool", role="secondary")
        
        self.sig_controls = QFrame()
        sig_controls_layout = QVBoxLayout(self.sig_controls)
        sig_controls_layout.setContentsMargins(0, 4, 0, 0)
        sig_controls_layout.setSpacing(2)
        
        scale_label = QLabel(qt_t("doc_scan.sig_scale", "Marker Scale"))
        scale_label.setObjectName("muted")
        scale_label.setStyleSheet("font-size: 11px;")
        
        self.sig_scale_slider = QSlider(Qt.Horizontal)
        self.sig_scale_slider.setRange(5, 50)
        self.sig_scale_slider.setValue(20)
        
        sig_controls_layout.addWidget(scale_label)
        sig_controls_layout.addWidget(self.sig_scale_slider)
        
        sig_layout.addWidget(self.load_sig_btn)
        sig_layout.addWidget(self.sig_controls)
        self.sig_controls.hide() # Hide until signature loaded
        
        self.param_panel.add_field(qt_t("doc_scan.signature", "Signature Overlay"), self.sig_box)

        # Global Actions
        self.reset_btn = build_icon_button(qt_t("doc_scan.reset", "Reset All Controls"), icon_name="rotate-ccw", role="secondary")
        self.param_panel.add_field("", self.reset_btn)
        
        # Save Buttons (Now fixed placeholders)
        self.save_png_btn = build_icon_button(qt_t("doc_scan.save_png", "Save Current Page (PNG)"), icon_name="image", role="primary")
        
        self.save_pdf_btn = build_icon_button(qt_t("doc_scan.save_pdf", "Merge All to PDF"), icon_name="file-text", role="primary")
        
        tools_layout.addWidget(self.param_panel, 1)
        tools_layout.addWidget(self.save_png_btn, 0)
        tools_layout.addWidget(self.save_pdf_btn, 0)

        self.splitter.addWidget(self.pages_card)
        self.splitter.addWidget(self.preview_card)
        self.splitter.addWidget(self.tools_card)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 7)
        self.splitter.setStretchFactor(2, 3)
        self.splitter.setSizes([200, 700, 300])
        
        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _bind_actions(self) -> None:
        self.page_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.rot_left_btn.clicked.connect(lambda: self._on_rotate(-90))
        self.rot_right_btn.clicked.connect(lambda: self._on_rotate(90))
        self.reset_btn.clicked.connect(self._on_reset)
        self.unwarp_btn.toggled.connect(self._on_unwarp_toggled)
        self.load_sig_btn.clicked.connect(self._on_load_signature)
        self.sig_scale_slider.valueChanged.connect(self._on_sig_scale_changed)
        
        self.filter_group.buttonClicked.connect(self._on_filter_changed)
        
        self.save_png_btn.clicked.connect(self._on_save_png)
        self.save_pdf_btn.clicked.connect(self._on_save_pdf)
        
        self.interactive_preview.changed.connect(self._refresh_preview)

    def _refresh_all(self) -> None:
        self._refresh_list()
        self._refresh_preview()
        self._refresh_tools()

    def _refresh_list(self) -> None:
        self.page_list.clear()
        for i, item in enumerate(self.state.items):
            list_item = QListWidgetItem(item.path.name)
            self.page_list.addItem(list_item)
            if i == self.state.current_index:
                self.page_list.setCurrentItem(list_item)
        
        self.header_surface.asset_count_badge.setText(f"{len(self.state.items)} pages")
        self.save_pdf_btn.setText(qt_t("doc_scan.save_pdf_count", f"Merge All to PDF ({len(self.state.items)} pages)"))

    def _on_selection_changed(self) -> None:
        self.state.current_index = self.page_list.currentRow()
        self._refresh_preview()
        self._refresh_tools()

    def _refresh_preview(self) -> None:
        if self.state.current_index < 0:
            self.interactive_preview.set_image(QPixmap())
            return
            
        cv_img = self.service.get_rendered_image(self.state.current_index, apply_signature=False)
        
        if cv_img is not None:
            rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w, c = rgb.shape
            bytes_per_line = c * w
            q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            self.interactive_preview.set_image(pixmap)

    def _refresh_tools(self) -> None:
        if self.state.current_index < 0:
            self.param_panel.setEnabled(False)
            self.save_png_btn.setEnabled(False)
            self.save_pdf_btn.setEnabled(False)
            return
            
        self.param_panel.setEnabled(True)
        self.save_png_btn.setEnabled(True)
        self.save_pdf_btn.setEnabled(True)
        
        item = self.state.items[self.state.current_index]
        self.unwarp_btn.blockSignals(True)
        self.unwarp_btn.setChecked(item.unwarp_active)
        self.unwarp_btn.blockSignals(False)
        
        if item.filter_type == "orig": self.radio_orig.setChecked(True)
        elif item.filter_type == "bw": self.radio_bw.setChecked(True)
        elif item.filter_type == "magic": self.radio_magic.setChecked(True)
        
        self.sig_scale_slider.setValue(int(item.signature_scale * 100))
        self.sig_controls.setVisible(self.state.signature_image is not None)

    def _on_rotate(self, delta: int) -> None:
        self.service.update_item_rotation(self.state.current_index, delta)
        self._refresh_preview()

    def _on_filter_changed(self, button: QRadioButton) -> None:
        mapping = {0: "orig", 1: "bw", 2: "magic"}
        f_type = mapping.get(self.filter_group.id(button), "orig")
        self.service.update_item_filter(self.state.current_index, f_type)
        self._refresh_preview()

    def _on_unwarp_toggled(self, checked: bool) -> None:
        self.service.set_unwarp(self.state.current_index, checked)
        self._refresh_preview()

    def _on_load_signature(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Signature PNG", "", "Images (*.png)")
        if path:
            if self.service.load_signature(path):
                # Set default pos to center for current item
                if self.state.current_index >= 0:
                    self.state.items[self.state.current_index].signature_pos = (0.5, 0.5)
                self._refresh_preview()

    def _on_sig_scale_changed(self, value: int) -> None:
        self.service.set_signature_scale(self.state.current_index, value / 100.0)
        self._refresh_preview()

    def _on_reset(self) -> None:
        self.service.reset_item(self.state.current_index)
        self._refresh_all()

    def _on_save_png(self) -> None:
        path = self.service.save_current_as_png(self.state.current_index)
        QMessageBox.information(self, APP_TITLE, f"Saved as PNG:\n{path}")

    def _on_save_pdf(self) -> None:
        path = self.service.save_all_as_pdf()
        QMessageBox.information(self, APP_TITLE, f"Batch saved as PDF:\n{path}")

    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
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
        
    window = DocScanWindow(state, Path(__file__).resolve().parents[3] / "document" / "doc_scan")
    window.show()
    return app.exec()
