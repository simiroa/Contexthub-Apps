from __future__ import annotations

import sys
import threading
from pathlib import Path

from contexthub.ui.qt.panels import ExportFoldoutPanel, FixedParameterPanel, PreviewListPanel
from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
)
from features.ai.bg_removal_service import BackgroundRemovalService

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QMainWindow,
        QPushButton,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for rmbg_background.") from exc

APP_ID = "rmbg_background"
APP_TITLE = qt_t("rmbg_background.title", "AI Background Removal")
APP_SUBTITLE = qt_t("rmbg_background.subtitle", "Remove background from images using AI")


class BackgroundRemovalWindow(QMainWindow):
    def __init__(self, service: BackgroundRemovalService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        
        self.is_running = False

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1280, 860)
        self.setMinimumSize(1000, 700)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs(targets)
        self._refresh_parameter_form()
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
        self.header_surface.set_header_visibility(show_subtitle=True, show_asset_count=True, show_runtime_status=True)
        self.asset_count_badge = self.header_surface.asset_count_badge
        self.runtime_status_badge = self.header_surface.runtime_status_badge
        self.header_surface.open_webui_btn.hide()
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        
        self.preview_list_panel = PreviewListPanel(
            preview_title=qt_t("rmbg_background.preview", "Preview"),
            list_title=qt_t("rmbg_background.input_list", "Inputs"),
            list_hint=qt_t("rmbg_background.list_hint", "Select an image to preview."),
        )
        
        right_card = QFrame()
        right_card.setObjectName("card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        right_layout.setSpacing(m.section_gap)

        self.param_panel = FixedParameterPanel(
            title=qt_t("rmbg_background.parameters", "Parameters"),
            description=qt_t("rmbg_background.param_desc", "Configure removal settings"),
        )
        self.param_panel.preset_label.hide()
        self.param_panel.preset_combo.hide()
        
        self.runtime_status_badge = self.header_surface.runtime_status_badge
        self.header_surface.open_webui_btn.hide()
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        
        self.preview_list_panel = PreviewListPanel(
            preview_title=qt_t("rmbg_background.preview", "Preview"),
            list_title=qt_t("rmbg_background.input_list", "Inputs"),
            list_hint=qt_t("rmbg_background.list_hint", "Select an image to preview."),
        )
        
        right_card = QFrame()
        right_card.setObjectName("card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        right_layout.setSpacing(m.section_gap)

        self.param_panel = FixedParameterPanel(
            title=qt_t("rmbg_background.parameters", "Parameters"),
            description=qt_t("rmbg_background.param_desc", "Configure removal settings"),
        )
        self.param_panel.preset_label.hide()
        self.param_panel.preset_combo.hide()
        
        # Model Choice
        self.model_combo = QComboBox()
        self.model_combo.addItems(["birefnet", "inspyrenet", "rmbg"])
        self.model_combo.setCurrentText(self.service.state.model)
        self.param_panel.add_field(qt_t("rmbg_background.model", "Model"), self.model_combo)
        
        # Post-process Choice
        self.postprocess_combo = QComboBox()
        self.postprocess_combo.addItems(["none", "smooth", "sharpen", "feather"])
        self.postprocess_combo.setCurrentText(self.service.state.postprocess)
        self.param_panel.add_field(qt_t("rmbg_background.postprocess", "Post-process"), self.postprocess_combo)
        
        # Transparency Check
        self.transparent_check = QCheckBox(qt_t("rmbg_background.transparent", "Export with transparency (PNG)"))
        self.transparent_check.setChecked(self.service.state.transparent)
        self.param_panel.add_field("", self.transparent_check)
        
        # Download Button
        self.download_btn = QPushButton(qt_t("rmbg_background.download_models", "Download Models"))
        self.download_btn.setProperty("buttonRole", "pill")
        self.param_panel.add_field("", self.download_btn)

        right_layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportFoldoutPanel(qt_t("rmbg_background.export_and_run", "Process And Run"))
        right_layout.addWidget(self.export_panel, 0)
        
        self.splitter.addWidget(self.preview_list_panel)
        self.splitter.addWidget(right_card)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        
        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _bind_actions(self) -> None:
        self.preview_list_panel.add_requested.connect(self._pick_inputs)
        self.preview_list_panel.remove_requested.connect(self._remove_selected_input)
        self.preview_list_panel.clear_requested.connect(self._clear_inputs)
        self.preview_list_panel.selection_changed.connect(self._sync_preview_from_selection)
        
        self.model_combo.currentTextChanged.connect(lambda t: self.service.update_parameter("model", t))
        self.postprocess_combo.currentTextChanged.connect(lambda t: self.service.update_parameter("postprocess", t))
        self.transparent_check.toggled.connect(lambda c: self.service.update_parameter("transparent", c))
        self.download_btn.clicked.connect(self._on_download_models)

        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.export_panel.run_requested.connect(self._run_removal)
        self.export_panel.toggle_requested.connect(self._toggle_export_details)

    def _refresh_parameter_form(self) -> None:
        pass

    def _refresh_all(self) -> None:
        self._refresh_assets()
        self._refresh_runtime_status()

    def _refresh_runtime_status(self) -> None:
        label, tone = self.service.probe_runtime()
        self.runtime_status_badge.setText(label)

    def _refresh_assets(self) -> None:
        current_path = self.service.state.preview_path
        items: list[tuple[str, str]] = []
        for asset in self.service.state.input_assets:
            items.append((asset.path.name, str(asset.path)))
        self.preview_list_panel.set_items(items)
        
        if current_path:
            for index, asset in enumerate(self.service.state.input_assets):
                if asset.path == current_path:
                    self.preview_list_panel.input_list.setCurrentRow(index)
                    break
        elif self.service.state.input_assets:
            self.preview_list_panel.input_list.setCurrentRow(0)
            self.service.set_preview_from_index(0)
            
        self.asset_count_badge.setText(qt_t("rmbg_background.asset_count", "{count} files", count=len(self.service.state.input_assets)))
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        preview = self.service.state.preview_path
        if preview is None:
            self.preview_list_panel.set_preview(qt_t("rmbg_background.preview_empty", "Select an image to preview."), "")
            return
        self.preview_list_panel.set_preview(preview.name, str(preview))

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, APP_TITLE, "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tga *.tif *.tiff)")
        if not files:
            return
        self.service.add_inputs(files)
        self._refresh_assets()

    def _remove_selected_input(self) -> None:
        self.service.remove_input_at(self.preview_list_panel.current_row())
        self._refresh_assets()

    def _clear_inputs(self) -> None:
        self.service.clear_inputs()
        self._refresh_assets()

    def _sync_preview_from_selection(self) -> None:
        self.service.set_preview_from_index(self.preview_list_panel.current_row())
        self._refresh_preview()

    def _reveal_output_dir(self) -> None:
        self._sync_output_options()
        self.service.reveal_output_dir()

    def _sync_output_options(self) -> None:
        self.service.update_output_options(
            self.export_panel.output_dir_edit.text(),
            self.export_panel.output_prefix_edit.text(),
            self.export_panel.open_folder_after_run.isChecked(),
            self.export_panel.export_session_checkbox.isChecked(),
        )
        self.export_panel.refresh_summary()

    def _on_download_models(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.runtime_status_badge.setText(qt_t("rmbg_background.downloading", "Downloading..."))
        
        def worker():
            process = self.service.download_models()
            for line in process.stdout:
                print(line, end="") # Log to console
            process.wait()
            
            def done():
                self.is_running = False
                self._refresh_runtime_status()
            QTimer.singleShot(0, done)

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def _run_removal(self) -> None:
        if self.is_running or not self.service.state.input_assets:
            return
        
        self._sync_output_options()
        self.is_running = True
        self.runtime_status_badge.setText(qt_t("rmbg_background.running", "Running..."))
        self.export_panel.run_btn.setEnabled(False)
        
        def worker():
            total = len(self.service.state.input_assets)
            for index, asset in enumerate(self.service.state.input_assets):
                process = self.service.run_workflow(asset.path)
                stdout, _ = process.communicate()
                print(stdout) # Log to console
            
            def done():
                self.is_running = False
                self.export_panel.run_btn.setEnabled(True)
                self.runtime_status_badge.setText(qt_t("rmbg_background.ready", "Ready"))
                if self.service.state.output_options.open_folder_after_run:
                    self.service.reveal_output_dir()
            QTimer.singleShot(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _toggle_export_details(self) -> None:
        self.export_panel.set_expanded(not self.export_panel.details.isVisible())

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
    window = BackgroundRemovalWindow(BackgroundRemovalService(), Path(__file__).resolve().parents[3] / "ai" / "rmbg_background", targets)
    window.show()
    return app.exec()
