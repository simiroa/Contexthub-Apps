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
from features.ai.upscale_service import UpscaleService

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
    raise ImportError("PySide6 is required for esrgan_upscale.") from exc

APP_ID = "esrgan_upscale"
APP_TITLE = qt_t("esrgan_upscale.title", "AI Image Upscaler")
APP_SUBTITLE = qt_t("esrgan_upscale.subtitle", "Enhance image resolution using Real-ESRGAN")


class UpscaleWindow(QMainWindow):
    def __init__(self, service: UpscaleService, app_root: str | Path, targets: list[str] | None = None) -> None:
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
        root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)
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
            preview_title=qt_t("esrgan_upscale.preview", "Preview"),
            list_title=qt_t("esrgan_upscale.input_list", "Inputs"),
            list_hint=qt_t("esrgan_upscale.list_hint", "Select an image to preview."),
        )
        
        right_card = QFrame()
        right_card.setObjectName("card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        right_layout.setSpacing(m.section_gap)

        self.param_panel = FixedParameterPanel(
            title=qt_t("esrgan_upscale.parameters", "Parameters"),
            description=qt_t("esrgan_upscale.param_desc", "Configure upscale settings"),
        )
        self.param_panel.preset_label.hide()
        self.param_panel.preset_combo.hide() # ESRGAN doesn't use presets in this version
        
        # Scale Choice
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["2", "4"])
        self.scale_combo.setCurrentText(self.service.state.scale)
        self.param_panel.add_field(qt_t("esrgan_upscale.scale", "Scale"), self.scale_combo)
        
        # Face Enhance
        self.face_check = QCheckBox(qt_t("esrgan_upscale.face_enhance", "Face Enhance (GFPGAN)"))
        self.face_check.setChecked(self.service.state.face_enhance)
        self.param_panel.add_field("", self.face_check)
        
        # Use Tile
        self.tile_check = QCheckBox(qt_t("esrgan_upscale.use_tile", "Use Tiling for low VRAM"))
        self.tile_check.setChecked(self.service.state.use_tile)
        self.param_panel.add_field("", self.tile_check)

        # Download Button
        self.download_btn = QPushButton(qt_t("esrgan_upscale.download_models", "Download Models"))
        self.download_btn.setObjectName("pillBtn")
        self.param_panel.add_field("", self.download_btn)

        right_layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportFoldoutPanel(qt_t("esrgan_upscale.export_and_run", "Upscale And Run"))
        # Using default prefix from state
        self.export_panel.set_values(
            "",
            self.service.state.output_options.file_prefix,
            self.service.state.output_options.open_folder_after_run,
            self.service.state.output_options.export_session_json,
        )
        self.export_panel.set_expanded(False)
        self.export_panel.export_btn.hide() # We don't need "Export Session" for this app
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
        
        self.scale_combo.currentTextChanged.connect(lambda t: self.service.update_parameter("scale", t))
        self.face_check.toggled.connect(lambda c: self.service.update_parameter("face_enhance", c))
        self.tile_check.toggled.connect(lambda c: self.service.update_parameter("use_tile", c))
        self.download_btn.clicked.connect(self._on_download_models)

        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.export_panel.run_requested.connect(self._run_upscale)
        self.export_panel.toggle_requested.connect(self._toggle_export_details)

    def _refresh_parameter_form(self) -> None:
        # Initial refresh if needed
        pass

    def _refresh_all(self) -> None:
        self._refresh_assets()
        self._refresh_runtime_status()

    def _refresh_runtime_status(self) -> None:
        label, tone = self.service.probe_runtime()
        self.runtime_status_badge.setText(label)
        # TODO: apply tone to badge color if shell supports it

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
            
        self.asset_count_badge.setText(qt_t("esrgan_upscale.asset_count", "{count} files", count=len(self.service.state.input_assets)))
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        preview = self.service.state.preview_path
        if preview is None:
            self.preview_list_panel.set_preview(qt_t("esrgan_upscale.preview_empty", "Select an image to preview."), "")
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
            self.export_panel.open_folder_checkbox.isChecked(),
            self.export_panel.export_session_checkbox.isChecked(),
        )
        self.export_panel.refresh_summary()

    def _on_download_models(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.runtime_status_badge.setText(qt_t("esrgan_upscale.downloading", "Downloading..."))
        
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

    def _run_upscale(self) -> None:
        if self.is_running or not self.service.state.input_assets:
            return
        
        self._sync_output_options()
        self.is_running = True
        self.runtime_status_badge.setText(qt_t("esrgan_upscale.running", "Running..."))
        self.export_panel.run_btn.setEnabled(False)
        
        def worker():
            process = self.service.run_workflow()
            for line in process.stdout:
                line = line.strip()
                if line:
                    print(line)
                    if line.startswith("[") and "/" in line:
                        # Update status from thread safely? 
                        # For now just log, maybe add a signal later if needed.
                        pass
            process.wait()
            
            def done():
                self.is_running = False
                self.export_panel.run_btn.setEnabled(True)
                self._refresh_runtime_status()
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
    window = UpscaleWindow(UpscaleService(), Path(__file__).resolve().parents[3] / "ai" / "esrgan_upscale", targets)
    window.show()
    return app.exec()
