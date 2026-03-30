from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Dict, Callable

from contexthub.ui.qt.panels import ExportFoldoutPanel, FixedParameterPanel, ComparativePreviewWidget
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
from features.image.vectorizer.rigreader_vectorizer_service import RigreaderVectorizerService

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, QPoint, QRect, QSize, Signal
    from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLineEdit,
        QMainWindow,
        QSplitter,
        QVBoxLayout,
        QWidget,
        QCheckBox,
        QSpinBox,
        QMessageBox,
        QListWidget,
        QListWidgetItem,
        QLabel,
        QPushButton,
        QSizePolicy,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required.") from exc

APP_ID = "rigreader_vectorizer"
APP_TITLE = qt_t("rigreader_vectorizer.title", "RigReady Vectorizer")
APP_SUBTITLE = qt_t("rigreader_vectorizer.subtitle", "Professional SVG vectorization for character rigging.")

class RiggingPreviewWidget(ComparativePreviewWidget):
    """Professional inspector area with rigging anchor visualization and split-slider."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.anchor_data = None
        self.comparison_enabled = False
        self.pixmaps: list[QPixmap] = []
        self.setMouseTracking(True)

    def set_pixmap_list(self, pixmaps: list[QPixmap]) -> None:
        self.pixmaps = [pm for pm in pixmaps if pm and not pm.isNull()]
        left = self.pixmaps[0] if self.pixmaps else QPixmap()
        right = self.pixmaps[1] if len(self.pixmaps) > 1 else QPixmap()
        self.set_pixmaps(left, right)

    def set_anchor_data(self, data: dict | None):
        self.anchor_data = data
        self.update()

    def set_comparison_enabled(self, enabled: bool):
        self.comparison_enabled = enabled
        self.set_mode("split" if enabled else "single")
        self.update()

    def mouseMoveEvent(self, event):
        if self.comparison_enabled and self.mode == "split":
            super().mouseMoveEvent(event)

    def paintEvent(self, event):
        if not self.pixmaps:
            painter = QPainter(self)
            painter.setPen(QColor(255, 255, 255, 60))
            painter.drawText(self.rect(), Qt.AlignCenter, qt_t("vectorizer.no_image", "Drop Artwork to Begin"))
            painter.end()
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # 1. Image Drawing
        pm_primary = self.pixmaps[0]
        if not pm_primary.isNull():
            if self.mode == "single":
                pm = pm_primary.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                draw_rect = QRect(rect.center() - pm.rect().center(), pm.size())
                painter.drawPixmap(draw_rect, pm)
            elif self.mode == "split" and len(self.pixmaps) > 1:
                pm_sec = self.pixmaps[1]
                l_pm = pm_primary.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                draw_rect = QRect(rect.center() - l_pm.rect().center(), l_pm.size())
                
                # Original (Left)
                painter.drawPixmap(draw_rect, l_pm)
                
                # Result (Right with Clip)
                if not pm_sec.isNull():
                    painter.save()
                    split_x = int(draw_rect.width() * self.split_ratio)
                    painter.setClipRect(QRect(draw_rect.x() + split_x, draw_rect.y(), draw_rect.width() - split_x, draw_rect.height()))
                    r_pm = pm_sec.scaled(draw_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    painter.drawPixmap(draw_rect, r_pm)
                    painter.restore()
                    
                    # Slider handle
                    slider_x = draw_rect.x() + split_x
                    painter.setPen(QPen(Qt.white, 1))
                    painter.drawLine(slider_x, draw_rect.y(), slider_x, draw_rect.y() + draw_rect.height())

        # 2. Labels (Top/Bottom corners)
        if self.mode == "split":
            font = QFont("Inter", 10, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255, 180))
            
            # Left: Original
            painter.fillRect(QRect(12, 12, 45, 20), QColor(0, 0, 0, 140))
            painter.drawText(QRect(12, 12, 45, 20), Qt.AlignCenter, "ORIG")
            
            # Right: SVG
            painter.fillRect(QRect(rect.width() - 57, 12, 45, 20), QColor(0, 0, 0, 140))
            painter.drawText(QRect(rect.width() - 57, 12, 45, 20), Qt.AlignCenter, "SVG")

        # 3. Rigging Anchors
        if self.anchor_data:
            idx = 1 if len(self.pixmaps) > 1 and self.mode == "split" else 0
            pm = self.pixmaps[idx]
            if not pm.isNull():
                scaled_size = pm.size().scaled(rect.size(), Qt.KeepAspectRatio)
                dr = QRect(rect.center() - QPoint(scaled_size.width()/2, scaled_size.height()/2), scaled_size)
                
                px = dr.x() + (self.anchor_data["x"] / pm.width()) * dr.width()
                py = dr.y() + (self.anchor_data["y"] / pm.height()) * dr.height()
                
                painter.setPen(QPen(QColor(0, 255, 255, 220), 2))
                painter.drawLine(int(px - 12), int(py), int(px + 12), int(py))
                painter.drawLine(int(px), int(py - 12), int(px), int(py + 12))
                
                painter.setPen(QColor(0, 255, 255))
                painter.drawText(int(px + 10), int(py - 10), self.anchor_data["name"])
        
        painter.end()

class LayerNavigatorPanel(QFrame):
    """Custom navigator for character layers and results. NO 'Add File' buttons."""
    selectionChanged = Signal()

    def __init__(self, title: str = "Navigator"):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(8)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        layout.addWidget(self.title_label)
        
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("navigatorList")
        palette = get_shell_palette()
        ss = "QListWidget#navigatorList { border: none; background: transparent; } "
        ss += "QListWidget#navigatorList::item { padding: 8px; border-radius: 4px; margin-bottom: 2px; } "
        ss += f"QListWidget#navigatorList::item:selected {{ background: {palette.accent_soft}; color: {palette.chip_text}; }} "
        ss += f"QListWidget#navigatorList::item:hover:!selected {{ background: {palette.button_hover}; }}"
        self.list_widget.setStyleSheet(ss)
        layout.addWidget(self.list_widget, 1)
        
        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)
        
        self.list_widget.currentRowChanged.connect(lambda _: self.selectionChanged.emit())

    def set_items(self, items: List[tuple[str, str]]):
        self.list_widget.clear()
        for display_name, uid in items:
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, uid)
            self.list_widget.addItem(item)

    def current_uid(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

class VectorizerWindow(QMainWindow):
    def __init__(self, service: RigreaderVectorizerService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._field_widgets: dict[str, QWidget] = {}

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1300, 900)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs(targets)
            
        self._refresh_presets()
        self._refresh_parameter_form()
        self._refresh_ui()
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin-2, m.shell_margin-2, m.shell_margin-2, m.shell_margin-2)
        
        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)
        
        # 1. Header with Source Loading
        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root, show_webui=True)
        self.header_surface.set_header_visibility(show_subtitle=True, show_asset_count=True, show_runtime_status=True)
        self.header_surface.open_webui_btn.setText("Open Artwork")
        self.header_surface.open_webui_btn.setToolTip("Select source character artwork")
        shell_layout.addWidget(self.header_surface)
        
        # 2. Main 3-Panel Splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(8)
        
        # Left: Navigator
        self.navigator = LayerNavigatorPanel("Structure")
        self.main_splitter.addWidget(self.navigator)
        
        # Middle: Inspector
        self.preview_card = QFrame()
        self.preview_card.setObjectName("card")
        pc_layout = QVBoxLayout(self.preview_card)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        self.inspector = RiggingPreviewWidget()
        pc_layout.addWidget(self.inspector)
        self.main_splitter.addWidget(self.preview_card)
        
        # Right: Configuration
        self.right_panel = QFrame()
        self.right_panel.setObjectName("panelCard")
        rp_layout = QVBoxLayout(self.right_panel)
        rp_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        rp_layout.setSpacing(m.section_gap)
        
        self.param_panel = FixedParameterPanel("Tracer Config", "Tweak rigging & path generation.")
        rp_layout.addWidget(self.param_panel, 1)
        
        self.export_panel = ExportFoldoutPanel("Execution")
        for w in [self.export_panel.output_prefix_label, self.export_panel.output_prefix_edit,
                 self.export_panel.toggle_btn, self.export_panel.export_btn, self.export_panel.export_session_checkbox]:
            w.hide()
        self.export_panel.set_expanded(True)
        self.export_panel.setMinimumHeight(150)
        rp_layout.addWidget(self.export_panel, 0)
        
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 6)
        self.main_splitter.setStretchFactor(2, 2)
        shell_layout.addWidget(self.main_splitter, 1)
        
        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _bind_actions(self) -> None:
        self.header_surface.open_webui_btn.clicked.connect(self._pick_source)
        self.navigator.selectionChanged.connect(self._on_navigator_selection)
        self.param_panel.preset_combo.currentTextChanged.connect(self.service.select_workflow)
        self.export_panel.run_requested.connect(self._run_vectorization)
        self.export_panel.reveal_requested.connect(self.service.reveal_output_dir)

    def _pick_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Artwork", "", "Artwork (*.psd *.psb *.png *.jpg *.tga)")
        if path:
            self.service.add_inputs([path])
            self._refresh_ui()

    def _on_navigator_selection(self) -> None:
        uid = self.navigator.current_uid()
        if uid:
            self.service.state.preview_uid = uid
            self._refresh_preview()

    def _refresh_ui(self) -> None:
        state = self.service.state
        assets = state.output_assets if state.current_mode == "output" else state.input_assets
        self.navigator.title_label.setText("Results (SVG)" if state.current_mode == "output" else "Structure")
        items = [(a.display_name, a.uid) for a in assets]
        self.navigator.set_items(items)
        if state.source_path:
            self.header_surface.set_asset_count(len(assets))
            self.header_surface.runtime_status_badge.setText(state.status_text or f"Source: {state.source_path.name}")
        if state.preview_uid:
            for i in range(self.navigator.list_widget.count()):
                if self.navigator.list_widget.item(i).data(Qt.UserRole) == state.preview_uid:
                    self.navigator.list_widget.setCurrentRow(i); break
        elif assets:
            self.navigator.list_widget.setCurrentRow(0)
        self._refresh_preview()
        self.export_panel.refresh_summary()
        self.export_panel.status_label.setText(state.status_text)

    def _refresh_preview(self) -> None:
        uid = self.service.state.preview_uid
        if not uid:
            self.inspector.set_pixmap_list([]); return
        pixmap = self.service.get_preview_pixmap(uid)
        if pixmap:
            if self.service.state.show_comparison:
                source_pm = self.service.get_source_pixmap()
                self.inspector.set_pixmap_list([source_pm if source_pm else pixmap, pixmap])
            else:
                self.inspector.set_pixmap_list([pixmap])
            self.inspector.set_anchor_data(self.service.get_anchor_preview_data(uid))
        else:
            self.inspector.set_pixmap_list([])

    def _run_vectorization(self) -> None:
        self.service.update_output_options(self.export_panel.output_dir_edit.text(), "", self.export_panel.open_folder_checkbox.isChecked(), False)
        self.export_panel.status_label.setText("Vectorizing...")
        def _on_finish(success, message):
            self.export_panel.status_label.setText(message)
            if success:
                self.service.state.current_mode = "output"
                self._refresh_ui()
                self.service.reveal_output_dir()
            else:
                QMessageBox.warning(self, "Error", message)
        ok, msg, _ = self.service.run_workflow(on_complete=_on_finish)
        if not ok: QMessageBox.warning(self, "Warning", msg)

    def _refresh_presets(self) -> None:
        cb = self.param_panel.preset_combo
        cb.blockSignals(True); cb.clear(); cb.addItems(self.service.get_workflow_names()); cb.setCurrentText(self.service.state.workflow_name); cb.blockSignals(False)

    def _refresh_parameter_form(self) -> None:
        self.param_panel.clear_fields()
        for defn in self.service.get_ui_definition():
            key = defn["key"]; val = getattr(self.service.state, key)
            if defn.get("type", "string") == "bool":
                w = QCheckBox(); w.setChecked(bool(val))
                def _on_t(v, k=key):
                    self.service.update_parameter(k, v)
                    if k == "show_comparison": self.inspector.set_comparison_enabled(v); self._refresh_preview()
                w.toggled.connect(_on_t)
            elif defn.get("type", "string") == "int":
                w = QSpinBox(); w.setRange(defn.get("min",0), defn.get("max",100)); w.setValue(int(val))
                w.valueChanged.connect(lambda v, k=key: self.service.update_parameter(k, v))
            else:
                w = QLineEdit(str(val)); w.textChanged.connect(lambda t, k=key: self.service.update_parameter(k, t))
            self.param_panel.add_field(defn["label"], w)

    def _check_runtime_preferences(self) -> None:
        sig = runtime_settings_signature()
        if sig != self._runtime_signature:
            self._runtime_signature = sig; refresh_runtime_preferences(); self.setStyleSheet(build_shell_stylesheet())

    def _restore_window_state(self) -> None:
        geom = self._settings.value("geometry")
        if geom: self.restoreGeometry(geom)

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry()); super().closeEvent(event)

def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    service = RigreaderVectorizerService()
    app_root = Path(__file__).resolve().parents[4] / "rigreader_vectorizer"
    window = VectorizerWindow(service, app_root, targets)
    window.show()
    return app.exec()
