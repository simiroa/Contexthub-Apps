from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.panels import ExportFoldoutPanel, FixedParameterPanel
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
from features.ai.marigold_pbr_service import MarigoldPBRService

try:
    import ctypes
    from PySide6.QtCore import QSettings, Qt, QTimer, Signal
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for marigold_pbr.") from exc

APP_ID = "marigold_pbr"
APP_TITLE = qt_t("marigold_gui.title", "Marigold PBR")
APP_SUBTITLE = qt_t("marigold_gui.header", "Generate depth, normal, and material maps from a single image.")


class MapSwitcher(QFrame):
    map_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("subtlePanel")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 6, 8, 6)
        self.layout.setSpacing(8)
        self.buttons: dict[str, QPushButton] = {}

    def set_available_maps(self, labels: list[str]) -> None:
        # Clear existing
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons.clear()

        for label in labels:
            btn = QPushButton(label)
            btn.setProperty("buttonRole", "pill")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, l=label: self.map_selected.emit(l))
            self.layout.addWidget(btn)
            self.buttons[label] = btn
        self.layout.addStretch(1)


class MarigoldPBRWindow(QMainWindow):
    map_selected = Signal(str) # "Original", "Depth", "Normal", etc.

    def __init__(self, service: MarigoldPBRService, app_root: Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = app_root
        self.targets = targets
        self.setObjectName("card")
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._field_widgets: dict[str, QWidget] = {}
        self.current_preview_kind = "Original"

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1340, 900)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs(targets)
        self._refresh_presets()
        self._refresh_parameter_form()
        self._refresh_all()
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        p = get_shell_palette()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)
        root.setSpacing(0)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root, show_webui=False)
        self.header_surface.set_header_visibility(show_subtitle=True, show_asset_count=False, show_runtime_status=True)
        self.runtime_status_badge = self.header_surface.runtime_status_badge
        shell_layout.addWidget(self.header_surface)

        # Splitter Layout
        self.main_split = QSplitter(Qt.Horizontal)
        
        # --- LEFT: Workspace Area ---
        self.workspace = QWidget()
        workspace_layout = QVBoxLayout(self.workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(m.section_gap)

        # 1. Main Viewer Card
        self.viewer_card = QFrame()
        self.viewer_card.setObjectName("card")
        viewer_layout = QVBoxLayout(self.viewer_card)
        viewer_layout.setContentsMargins(1, 1, 1, 1)

        self.viewer_label = QLabel(qt_t("ai_common.drop_hint", "Drop an image here to start"))
        self.viewer_label.setAlignment(Qt.AlignCenter)
        self.viewer_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        viewer_layout.addWidget(self.viewer_label)
        workspace_layout.addWidget(self.viewer_card, 1)

        # 2. Footer Row (Switcher + Action)
        self.footer_row = QHBoxLayout()
        self.add_btn = QPushButton(qt_t("common.add", "Add Image"))
        self.add_btn.setProperty("buttonRole", "pill")
        self.footer_row.addWidget(self.add_btn)

        self.switcher = MapSwitcher()
        self.footer_row.addWidget(self.switcher, 1)
        workspace_layout.addLayout(self.footer_row)

        # --- RIGHT: Settings Panel ---
        self.settings_container = QFrame()
        self.settings_container.setObjectName("card")
        settings_layout = QVBoxLayout(self.settings_container)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        settings_layout.setSpacing(m.section_gap)

        settings_header = QHBoxLayout()
        settings_header.setContentsMargins(0, 0, 0, 0)
        settings_header.setSpacing(8)
        self.download_btn = QPushButton(qt_t("marigold_gui.download_models", "Check Models"))
        self.download_btn.setProperty("buttonRole", "pill")
        self.download_btn.setToolTip(qt_t("marigold_gui.download_models", "Download/Check Models"))
        settings_header.addStretch(1)
        settings_header.addWidget(self.download_btn, 0)
        settings_layout.addLayout(settings_header)

        self.param_panel = FixedParameterPanel(
            title=qt_t("marigold_gui.settings", "Generation Control"),
            description="",
            preset_label=qt_t("marigold_gui.quality_label", "Quality Preset"),
        )
        self.workflow_description = self.param_panel.description_label
        self.workflow_description.setStyleSheet(f"margin-top: -5px; margin-bottom: 5px; color: {p.text_muted};")
        settings_layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportFoldoutPanel(qt_t("marigold_gui.export", "Export Options"))
        settings_layout.addWidget(self.export_panel, 0)

        self.main_split.addWidget(self.workspace)
        self.main_split.addWidget(self.settings_container)
        self.main_split.setStretchFactor(0, 1)
        self.main_split.setStretchFactor(1, 0)
        self.main_split.setSizes([850, 420])
        
        shell_layout.addWidget(self.main_split, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        
        root.addWidget(self.window_shell)

    def _bind_actions(self) -> None:
        self.add_btn.clicked.connect(self._pick_inputs)
        self.switcher.map_selected.connect(self._switch_preview)
        self.param_panel.preset_combo.currentTextChanged.connect(self._on_workflow_changed)
        self.download_btn.clicked.connect(self._download_models)
        self.export_panel.run_requested.connect(self._run_workflow)
        self.export_panel.reveal_requested.connect(self.service.reveal_output_dir)
        self.export_panel.toggle_requested.connect(lambda: self.export_panel.set_expanded(not self.export_panel.details.isVisible()))

    def _refresh_presets(self) -> None:
        combo = self.param_panel.preset_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(self.service.get_workflow_names())
        if self.service.state.workflow_name:
            combo.setCurrentText(self.service.state.workflow_name)
        combo.blockSignals(False)

    def _refresh_parameter_form(self) -> None:
        self.param_panel.clear_fields()
        self._field_widgets.clear()
        self.workflow_description.setText(self.service.state.workflow_description)

        for section_def in self.service.get_ui_definition():
            section_card = QFrame()
            section_card.setObjectName("subtlePanel")
            section_layout = QVBoxLayout(section_card)
            section_layout.setContentsMargins(10, 8, 10, 8)
            section_layout.setSpacing(6)
            
            title = QLabel(section_def["section"].upper())
            title.setObjectName("eyebrow")
            title.setStyleSheet(f"color: {get_shell_palette().accent}; font-weight: bold;")
            section_layout.addWidget(title)

            # Use Grid for bools if multiple, else vertical
            grid_layout = QGridLayout()
            grid_layout.setSpacing(8)
            col, row = 0, 0
            
            for item in section_def["items"]:
                key, label, kind = str(item["key"]), str(item["label"]), str(item.get("type", "string"))
                value = self.service.state.parameter_values.get(key, item.get("default"))

                if kind == "bool":
                    widget = QCheckBox(label)
                    widget.setChecked(bool(value))
                    widget.toggled.connect(lambda v, k=key: self.service.update_parameter(k, v))
                    grid_layout.addWidget(widget, row, col)
                    col += 1
                    if col > 1:
                        col = 0
                        row += 1
                else:
                    item_vbox = QVBoxLayout()
                    item_vbox.setSpacing(2)
                    item_vbox.addWidget(QLabel(label))
                    if kind == "choice":
                        widget = QComboBox()
                        widget.addItems([str(o) for o in item.get("options", [])])
                        widget.setCurrentText(str(value))
                        widget.currentTextChanged.connect(lambda v, k=key: self.service.update_parameter(k, v))
                    else:
                        widget = QLineEdit(str(value))
                        widget.textChanged.connect(lambda v, k=key: self.service.update_parameter(k, v))
                    item_vbox.addWidget(widget)
                    section_layout.addLayout(item_vbox)
                    self._field_widgets[key] = widget
            
            if grid_layout.count() > 0:
                section_layout.addLayout(grid_layout)
                
            self.param_panel.form_body.addWidget(section_card)

    def _pick_inputs(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self.service.add_inputs([path])
            self.current_preview_kind = "Original"
            self._refresh_all()

    def _refresh_all(self) -> None:
        state = self.service.state
        self._sync_preview()
        
        # Switcher labels: Original + Selected Maps
        labels = ["Original"]
        if state.preview_path:
            p = state.preview_path
            for m in ["depth", "normal", "albedo", "roughness", "metallicity", "orm"]:
                if (p.parent / f"{p.stem}_{m}.png").exists():
                    labels.append(m.capitalize())
        self.switcher.set_available_maps(labels)
        
        status, mode = self.service.probe_runtime()
        self.runtime_status_badge.setText(status)
        self.export_panel.refresh_summary()

    def _sync_preview(self) -> None:
        path = self.service.state.preview_path
        if not path:
            self.viewer_label.setPixmap(QPixmap())
            self.viewer_label.setText(qt_t("ai_common.drop_hint", "Add an image to start"))
            return
            
        target_path = path
        if self.current_preview_kind != "Original":
            suffix = self.current_preview_kind.lower()
            candidate = path.parent / f"{path.stem}_{suffix}.png"
            if candidate.exists():
                target_path = candidate

        image = QImage(str(target_path))
        if not image.isNull():
            pixmap = QPixmap.fromImage(image).scaled(
                self.viewer_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.viewer_label.setPixmap(pixmap)
            self.viewer_label.setText("")

    def _switch_preview(self, kind: str) -> None:
        self.current_preview_kind = kind
        self._sync_preview()

    def _on_workflow_changed(self, name: str) -> None:
        if name:
            self.service.select_workflow(name)
            self._refresh_parameter_form()

    def _download_models(self) -> None:
        self.download_btn.setEnabled(False)
        self.runtime_status_badge.setText("Downloading...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ok, message = self.service.download_models(lambda m: self.runtime_status_badge.setText(m))
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Model Setup", message)
            self._refresh_all()
        finally:
            QApplication.restoreOverrideCursor()
            self.download_btn.setEnabled(True)

    def _run_workflow(self) -> None:
        self.export_panel.run_btn.setEnabled(False)
        self.export_panel.status_label.setText("Processing...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ok, message, _ = self.service.run_workflow(lambda m: self.export_panel.status_label.setText(m))
            self.export_panel.status_label.setText(message)
            if ok:
                self._refresh_all()
        finally:
            QApplication.restoreOverrideCursor()
            self.export_panel.run_btn.setEnabled(True)

    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current != self._runtime_signature:
            self._runtime_signature = current
            refresh_runtime_preferences()
            self.setStyleSheet(build_shell_stylesheet())

    def _restore_window_state(self) -> None:
        geom = self._settings.value("geometry")
        if geom: self.restoreGeometry(geom)

    def resizeEvent(self, event) -> None:
        self._sync_preview()
        super().resizeEvent(event)

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MarigoldPBRWindow(MarigoldPBRService(), Path(__file__).resolve().parents[3] / "marigold_pbr", targets)
    window.show()
    return app.exec()
