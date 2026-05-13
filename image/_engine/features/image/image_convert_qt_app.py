from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.panels import ExportRunPanel, FixedParameterPanel
from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    build_shell_stylesheet,
    get_shell_metrics,
    get_shell_palette,
    qt_t,
)
from features.image.image_convert_service import ImageConvertService
from shared._engine.runtime.base_window import BaseAppWindow
from shared._engine.runtime.media_runtime import MediaRuntime
from shared._engine.runtime.file_input_mixin import MultiFileInputMixin
from shared._engine.components.batch_list_card import build_batch_list_card

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLineEdit,
        QSplitter,
        QTextEdit,
        QVBoxLayout,
        QWidget,
        QLabel,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for image_convert.") from exc

APP_ID = "image_convert"
APP_TITLE = qt_t("image_convert.title", "Image Converter")
APP_SUBTITLE = qt_t("image_convert.subtitle", "Batch convert images efficiently.")

class ImageConvertWindow(BaseAppWindow, MultiFileInputMixin):
    APP_ID = "image_convert"

    def __init__(self, service: ImageConvertService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__(app_root)
        self.service = service
        self.runtime = MediaRuntime.instance()
        self._field_widgets: dict[str, QWidget] = {}

        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        # Initialize Mixin
        self.setup_file_inputs(
            self.batch_ui["add_btn"], 
            self.batch_ui["clear_btn"], 
            self.batch_ui["list_widget"], 
            self.service.state
        )
        if targets:
            self.handle_external_targets(targets)
            
        self._refresh_presets()
        self._refresh_parameter_form()
        self._refresh_stats()
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
        self.header_surface.set_header_visibility(show_subtitle=False, show_asset_count=True)
        self.asset_count_badge = self.header_surface.asset_count_badge
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        
        # Left: Batch List
        self.batch_ui = build_batch_list_card()
        self.splitter.addWidget(self.batch_ui["card"])
        
        # Right: Parameters
        right_panel = QFrame()
        right_panel.setObjectName("card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        
        self.param_panel = FixedParameterPanel(
            title=qt_t("image_convert.parameters", "Settings"),
            description=qt_t("image_convert.settings_desc", "Configure conversion options."),
            preset_label=qt_t("image_convert.preset", "Workflow"),
        )
        self.workflow_description = self.param_panel.description_label
        self.workflow_combo = self.param_panel.preset_combo
        right_layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportRunPanel(qt_t("image_convert.run", "Convert Now"))
        self.export_panel.set_values(
            str(self.service.state.output_options.output_dir),
            self.service.state.output_options.file_prefix,
            self.service.state.output_options.open_folder_after_run,
            self.service.state.output_options.export_session_json,
        )
        self.export_panel.set_expanded(False)
        right_layout.addWidget(self.export_panel, 0)
        
        self.splitter.addWidget(right_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def get_file_filters(self):
        return "Images (*.png *.jpg *.jpeg *.webp *.bmp *.ico *.exr)"

    def on_files_added(self, paths):
        self._refresh_stats()

    def on_files_cleared(self):
        self._refresh_stats()

    def load_thumbnail(self, path):
        return self.runtime.get_image(path)

    def _refresh_stats(self):
        count = len(self.service.state.files)
        self.asset_count_badge.setText(qt_t("image_convert.asset_count", "{count} images", count=count))

    def _bind_actions(self) -> None:
        self.workflow_combo.currentTextChanged.connect(self._on_workflow_changed)
        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.export_panel.run_requested.connect(self._run_conversion)
        self.export_panel.toggle_requested.connect(lambda: self.export_panel.set_expanded(not self.export_panel.details.isVisible()))

    def _refresh_presets(self) -> None:
        names = self.service.get_workflow_names()
        self.workflow_combo.blockSignals(True)
        self.workflow_combo.clear()
        self.workflow_combo.addItems(names)
        if self.service.state.workflow_name:
            index = self.workflow_combo.findText(self.service.state.workflow_name)
            if index >= 0:
                self.workflow_combo.setCurrentIndex(index)
        self.workflow_combo.blockSignals(False)

    def _refresh_parameter_form(self) -> None:
        self.param_panel.clear_fields()
        self._field_widgets.clear()
        self.workflow_description.setText(self.service.state.workflow_description)

        for definition in self.service.get_ui_definition():
            widget = self._create_param_widget(definition)
            self._field_widgets[str(definition["key"])] = widget
            self.param_panel.add_field(str(definition["label"]), widget)

    def _create_param_widget(self, definition: dict[str, object]) -> QWidget:
        key = str(definition["key"])
        kind = str(definition.get("type", "string"))
        value = self.service.state.parameter_values.get(key, definition.get("default"))

        if kind == "text":
            widget = QTextEdit()
            widget.setPlainText("" if value is None else str(value))
            widget.textChanged.connect(lambda k=key, w=widget: self.service.update_parameter(k, w.toPlainText()))
            return widget

        if kind == "choice":
            widget = QComboBox()
            widget.addItems([str(option) for option in definition.get("options", [])])
            if value is not None:
                widget.setCurrentText(str(value))
            widget.currentTextChanged.connect(lambda text, k=key: self.service.update_parameter(k, text))
            return widget

        widget = QLineEdit("" if value is None else str(value))
        widget.textChanged.connect(lambda text, k=key: self.service.update_parameter(k, text))
        return widget

    def _on_workflow_changed(self, name: str) -> None:
        if not name: return
        self.service.select_workflow(name)
        self._refresh_parameter_form()

    def _reveal_output_dir(self) -> None:
        self._sync_output_options()
        self.service.reveal_output_dir()

    def _run_conversion(self) -> None:
        if not self.service.state.files: return
        self._sync_output_options()
        self.export_panel.run_btn.setEnabled(False)
        self.export_panel.status_label.setText("Starting...")
        
        def on_progress(f, c, t):
            self.export_panel.status_label.setText(f"Converting: {c}/{t} ({int(f*100)}%)")
            
        def on_complete(count, errors):
            self.export_panel.run_btn.setEnabled(True)
            if errors:
                self.export_panel.status_label.setText(f"Done: {count} success, {len(errors)} errors.")
            else:
                self.export_panel.status_label.setText(f"Success: {count} images converted.")
            if self.service.state.output_options.open_folder_after_run:
                self.service.reveal_output_dir()

        self.service.run_workflow(on_progress, on_complete)

    def _sync_output_options(self) -> None:
        self.service.update_output_options(
            self.export_panel.output_dir_edit.text(),
            self.export_panel.output_prefix_edit.text(),
            self.export_panel.open_folder_checkbox.isChecked(),
            self.export_panel.export_session_checkbox.isChecked(),
        )
        self.export_panel.refresh_summary()



def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    
    from shared._engine.runtime.single_instance import SingleInstance
    si = SingleInstance(APP_ID)
    if si.is_already_running():
        if targets: si.send_to_primary(targets)
        return 0
        
    app_root = Path(__file__).resolve().parents[3] / "image" / "image_convert"
    try:
        from shared._engine.runtime.splash import show_splash, finish_splash
        splash = show_splash(app_root)
    except Exception:
        splash, finish_splash = None, lambda *_: None  # type: ignore[assignment]

    window = ImageConvertWindow(ImageConvertService(), app_root, targets)

    si.start_server()
    si.message_received.connect(window.handle_external_targets)
    window._si = si # Keep alive

    window.show()
    finish_splash(splash, window)
    return app.exec()
