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
from features.comfyui.ai_upscaler_service import AIUpscalerService
from features.comfyui.ai_upscaler_state import MODEL_CHOICES

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for ai_upscaler.") from exc


APP_ID = "ai_upscaler"
APP_TITLE = qt_t("ai_upscaler.title", "AI Image Upscaler")
APP_SUBTITLE = qt_t(
    "ai_upscaler.subtitle",
    "Upscale & restore via ComfyUI — Real-ESRGAN, DiffBIR-v2, SUPIR",
)


class AIUpscalerWindow(QMainWindow):
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, service: AIUpscalerService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(2000)
        self._runtime_timer.timeout.connect(self._on_runtime_tick)
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
        self._refresh_all()
        self._runtime_timer.start()

    # ---------- UI ----------
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
            preview_title=qt_t("ai_upscaler.preview", "Preview"),
            list_title=qt_t("ai_upscaler.input_list", "Inputs"),
            list_hint=qt_t("ai_upscaler.list_hint", "Select an image to preview."),
        )

        right_card = QFrame()
        right_card.setObjectName("card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        right_layout.setSpacing(m.section_gap)

        self.param_panel = FixedParameterPanel(
            title=qt_t("ai_upscaler.parameters", "Parameters"),
            description=qt_t("ai_upscaler.param_desc", "Pick a model and tweak run settings"),
        )
        self.param_panel.preset_label.hide()
        self.param_panel.preset_combo.hide()

        # Model selector
        self.model_combo = QComboBox()
        for key, label, _filename in MODEL_CHOICES:
            self.model_combo.addItem(label, key)
        idx = self.model_combo.findData(self.service.state.model_key)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.param_panel.add_field(qt_t("ai_upscaler.model", "Model"), self.model_combo)

        # Workflow status row
        self.workflow_status_label = QLabel("")
        self.workflow_status_label.setWordWrap(True)
        self.param_panel.add_field(qt_t("ai_upscaler.workflow", "Workflow"), self.workflow_status_label)

        # Workflows folder buttons row
        wf_buttons = QWidget()
        wf_row = QHBoxLayout(wf_buttons)
        wf_row.setContentsMargins(0, 0, 0, 0)
        wf_row.setSpacing(8)
        self.open_workflows_btn = QPushButton(qt_t("ai_upscaler.open_workflows", "Open workflows folder"))
        self.open_workflows_btn.setProperty("buttonRole", "pill")
        self.reload_workflows_btn = QPushButton(qt_t("ai_upscaler.reload_workflows", "Reload"))
        self.reload_workflows_btn.setProperty("buttonRole", "pill")
        wf_row.addWidget(self.open_workflows_btn, 1)
        wf_row.addWidget(self.reload_workflows_btn, 0)
        self.param_panel.add_field("", wf_buttons)

        # Scale
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["2", "4"])
        self.scale_combo.setCurrentText(self.service.state.scale)
        self.param_panel.add_field(qt_t("ai_upscaler.scale", "Scale"), self.scale_combo)

        # Seed row: checkbox + spin
        seed_row_widget = QWidget()
        seed_row = QHBoxLayout(seed_row_widget)
        seed_row.setContentsMargins(0, 0, 0, 0)
        seed_row.setSpacing(8)
        self.seed_check = QCheckBox(qt_t("ai_upscaler.use_seed", "Fixed seed"))
        self.seed_check.setChecked(self.service.state.use_seed)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2_147_483_647)
        self.seed_spin.setValue(int(self.service.state.seed))
        self.seed_spin.setEnabled(self.service.state.use_seed)
        seed_row.addWidget(self.seed_check, 0)
        seed_row.addWidget(self.seed_spin, 1)
        self.param_panel.add_field(qt_t("ai_upscaler.seed", "Seed"), seed_row_widget)

        right_layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportFoldoutPanel(qt_t("ai_upscaler.export_and_run", "Upscale And Run"))
        self.export_panel.set_values(
            "",
            self.service.state.output_options.file_prefix,
            self.service.state.output_options.open_folder_after_run,
            self.service.state.output_options.export_session_json,
        )
        self.export_panel.set_expanded(False)
        self.export_panel.export_btn.hide()
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

        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.scale_combo.currentTextChanged.connect(lambda t: self.service.update_parameter("scale", t))
        self.seed_check.toggled.connect(self._on_seed_toggle)
        self.seed_spin.valueChanged.connect(lambda v: self.service.update_parameter("seed", v))

        self.open_workflows_btn.clicked.connect(lambda: self.service.reveal_workflows_dir())
        self.reload_workflows_btn.clicked.connect(self._refresh_workflow_status)

        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.export_panel.run_requested.connect(self._run)
        self.export_panel.toggle_requested.connect(self._toggle_export_details)

        self.log_signal.connect(self._on_log)
        self.finished_signal.connect(self._on_finished)

    # ---------- handlers ----------
    @Slot(int)
    def _on_model_changed(self, _index: int) -> None:
        key = self.model_combo.currentData()
        if not key:
            return
        self.service.update_parameter("model", key)
        self._refresh_workflow_status()
        self._refresh_runtime_status()

    @Slot(bool)
    def _on_seed_toggle(self, checked: bool) -> None:
        self.service.update_parameter("use_seed", checked)
        self.seed_spin.setEnabled(checked)

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, APP_TITLE, "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)"
        )
        if files:
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

    def _toggle_export_details(self) -> None:
        self.export_panel.set_expanded(not self.export_panel.details.isVisible())

    # ---------- refresh ----------
    def _refresh_all(self) -> None:
        self._refresh_assets()
        self._refresh_workflow_status()
        self._refresh_runtime_status()

    def _refresh_assets(self) -> None:
        current_path = self.service.state.preview_path
        items = [(asset.path.name, str(asset.path)) for asset in self.service.state.input_assets]
        self.preview_list_panel.set_items(items)
        if current_path:
            for index, asset in enumerate(self.service.state.input_assets):
                if asset.path == current_path:
                    self.preview_list_panel.input_list.setCurrentRow(index)
                    break
        elif self.service.state.input_assets:
            self.preview_list_panel.input_list.setCurrentRow(0)
            self.service.set_preview_from_index(0)
        self.asset_count_badge.setText(
            qt_t("ai_upscaler.asset_count", "{count} files", count=len(self.service.state.input_assets))
        )
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        preview = self.service.state.preview_path
        if preview is None:
            self.preview_list_panel.set_preview(qt_t("ai_upscaler.preview_empty", "Select an image to preview."), "")
            return
        self.preview_list_panel.set_preview(preview.name, str(preview))

    def _refresh_workflow_status(self) -> None:
        ok, message = self.service.workflow_status()
        prefix = "✓" if ok else "⚠"
        self.workflow_status_label.setText(f"{prefix}  {message}")

    def _refresh_runtime_status(self) -> None:
        label, _tone = self.service.probe_runtime()
        self.runtime_status_badge.setText(label)

    def _on_runtime_tick(self) -> None:
        sig = runtime_settings_signature()
        if sig != self._runtime_signature:
            self._runtime_signature = sig
            refresh_runtime_preferences()
            self.setStyleSheet(build_shell_stylesheet())
        if not self.is_running:
            self._refresh_runtime_status()

    # ---------- run ----------
    def _run(self) -> None:
        if self.is_running:
            return
        if not self.service.state.input_assets:
            QMessageBox.information(self, APP_TITLE, qt_t("ai_upscaler.no_inputs", "Add at least one image first."))
            return
        ok, message = self.service.workflow_status()
        if not ok:
            QMessageBox.warning(self, APP_TITLE, message)
            return

        self._sync_output_options()
        self.is_running = True
        self.runtime_status_badge.setText(qt_t("ai_upscaler.running", "Running..."))
        self.export_panel.run_btn.setEnabled(False)

        def worker() -> None:
            try:
                self.service.run(log=lambda msg: self.log_signal.emit(msg))
                self.finished_signal.emit(True, "")
            except Exception as exc:  # noqa: BLE001
                self.finished_signal.emit(False, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def _on_log(self, message: str) -> None:
        print(message)

    @Slot(bool, str)
    def _on_finished(self, success: bool, error: str) -> None:
        self.is_running = False
        self.export_panel.run_btn.setEnabled(True)
        self._refresh_runtime_status()
        if not success:
            QMessageBox.critical(self, APP_TITLE, error or "Run failed.")
            return
        if self.service.state.output_options.open_folder_after_run:
            self.service.reveal_output_dir()

    # ---------- window state ----------
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
    app_root = Path(__file__).resolve().parents[3] / "ai_upscaler"
    window = AIUpscalerWindow(AIUpscalerService(), app_root, targets)
    window.show()
    return app.exec()
