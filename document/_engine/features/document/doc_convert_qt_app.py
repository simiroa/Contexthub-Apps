from __future__ import annotations

import sys
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
from features.document.doc_convert_service import DocConvertService

try:
    from PySide6.QtCore import QSettings, Qt, QTimer
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLineEdit,
        QMainWindow,
        QSplitter,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for doc_convert.") from exc

APP_ID = "doc_convert"
APP_TITLE = qt_t("doc_convert.title", "Convert Docs")
APP_SUBTITLE = qt_t("doc_convert.subtitle", "Professional document conversion tool.")


class DocConvertWindow(QMainWindow):
    def __init__(self, service: DocConvertService, app_root: str | Path, targets: list[str] | None = None) -> None:
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
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs(targets)
        
        self._refresh_presets()
        self._refresh_parameter_form()
        self._refresh_assets()
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
        self.header_surface.set_header_visibility(
            show_subtitle=False,
            show_asset_count=True,
            show_runtime_status=False,
        )
        self.asset_count_badge = self.header_surface.asset_count_badge
        self.runtime_status_badge = self.header_surface.runtime_status_badge
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        
        self.left_panel = PreviewListPanel(
            preview_title=qt_t("doc_convert.preview", "Preview"),
            list_title=qt_t("doc_convert.input_list", "Inputs"),
            list_hint=qt_t("doc_convert.list_hint", "Select an item to update the preview."),
        )
        self.preview_list_panel = self.left_panel
        
        self.right_panel = QFrame()
        self.right_panel.setObjectName("card")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        right_layout.setSpacing(m.section_gap)

        self.param_panel = FixedParameterPanel(
            title=qt_t("doc_convert.parameters", "Parameters"),
            description="",
            preset_label=qt_t("doc_convert.preset", "Preset"),
        )
        self.param_panel.preset_combo.hide() # We don't really have multiple presets yet, just one.
        self.param_panel.preset_label.hide()
        
        self.export_panel = ExportFoldoutPanel(qt_t("doc_convert.export_and_run", "Export And Run"))
        self.export_panel.set_values(
            str(self.service.state.output_options.output_dir),
            self.service.state.output_options.file_prefix,
            self.service.state.output_options.open_folder_after_run,
            self.service.state.output_options.export_session_json,
        )
        self.export_panel.set_expanded(True)
        
        right_layout.addWidget(self.param_panel, 1)
        right_layout.addWidget(self.export_panel, 0)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 5)
        
        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        
        root.addWidget(self.window_shell)

    def _bind_actions(self) -> None:
        self.preview_list_panel.add_requested.connect(self._pick_inputs)
        self.preview_list_panel.remove_requested.connect(self._remove_selected_input)
        self.preview_list_panel.clear_requested.connect(self._clear_inputs)
        self.preview_list_panel.selection_changed.connect(self._sync_preview_from_selection)
        
        self.export_panel.reveal_requested.connect(self.service.reveal_output_dir)
        self.export_panel.run_requested.connect(self._run_conversion)
        self.export_panel.toggle_requested.connect(self._toggle_export_details)

    def _refresh_presets(self) -> None:
        pass # Not used for now

    def _refresh_parameter_form(self) -> None:
        self.param_panel.clear_fields()
        self._field_widgets.clear()

        for definition in self.service.get_ui_definition():
            widget = self._create_param_widget(definition)
            self._field_widgets[str(definition["key"])] = widget
            self.param_panel.add_field(str(definition["label"]), widget)

    def _create_param_widget(self, definition: dict[str, object]) -> QWidget:
        key = str(definition["key"])
        kind = str(definition.get("type", "string"))
        value = self.service.state.parameter_values.get(key, definition.get("default"))

        if kind == "choice":
            widget = QComboBox()
            widget.addItems([str(option) for option in definition.get("options", [])])
            if value is not None:
                widget.setCurrentText(str(value))
            widget.currentTextChanged.connect(lambda text, k=key: self._on_param_changed(k, text))
            return widget

        widget = QLineEdit("" if value is None else str(value))
        widget.textChanged.connect(lambda text, k=key: self._on_param_changed(k, text))
        return widget

    def _on_param_changed(self, key: str, value: Any) -> None:
        self.service.update_parameter(key, value)
        if key == "target_format":
            self._refresh_parameter_form() # DPI might need to appear/disappear

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, APP_TITLE)
        if not files:
            return
        self.service.add_inputs(files)
        self._refresh_assets()
        self._refresh_parameter_form()

    def _remove_selected_input(self) -> None:
        self.service.remove_input_at(self.preview_list_panel.current_row())
        self._refresh_assets()
        self._refresh_parameter_form()

    def _clear_inputs(self) -> None:
        self.service.clear_inputs()
        self._refresh_assets()
        self._refresh_parameter_form()

    def _sync_preview_from_selection(self) -> None:
        self.service.set_preview_from_index(self.preview_list_panel.current_row())
        self._refresh_preview()

    def _refresh_assets(self) -> None:
        items: list[tuple[str, str]] = []
        for asset in self.service.state.input_assets:
            items.append((asset.path.name, str(asset.path)))
        self.preview_list_panel.set_items(items)
        
        count = len(self.service.state.input_assets)
        self.asset_count_badge.setText(qt_t("doc_convert.asset_count", "{count} files", count=count))
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        preview = self.service.state.preview_path
        if preview is None:
            self.preview_list_panel.set_preview(qt_t("doc_convert.preview_empty", "No preview available."), "")
            return
        # Since we don't have a real previewer for all doc types yet, we just show the name
        self.preview_list_panel.set_preview(preview.name, str(preview))

    def _run_conversion(self) -> None:
        self._sync_output_options()
        self.export_panel.run_btn.setEnabled(False)
        self.export_panel.progress_bar.setVisible(True)
        self.export_panel.status_label.setText("Starting...")

        def on_done(ok, message, _dir):
            self.export_panel.run_btn.setEnabled(True)
            self.export_panel.progress_bar.setVisible(False)
            self.export_panel.status_label.setText(message)
        # In a real app, this should be in a separate thread
        ok, message, last_dir = self.service.run_workflow()
        on_done(ok, message, last_dir)

    def _toggle_export_details(self) -> None:
        self.export_panel.set_expanded(not self.export_panel.details.isVisible())

    def _sync_output_options(self) -> None:
        self.service.update_output_options(
            self.export_panel.output_dir_edit.text(),
            self.export_panel.output_prefix_edit.text(),
            self.export_panel.open_folder_checkbox.isChecked(),
            self.export_panel.export_session_checkbox.isChecked(),
        )

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
    window = DocConvertWindow(DocConvertService(), Path(__file__).resolve().parents[3] / "doc_convert", targets)
    window.show()
    return app.exec()
