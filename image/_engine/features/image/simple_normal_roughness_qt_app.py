from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.panels import ExportRunPanel, FixedParameterPanel, PreviewListPanel
from contexthub.ui.qt.shell import (
    HeaderSurface,
    apply_app_icon,
    build_shell_stylesheet,
    build_size_grip,
    get_shell_metrics,
    get_shell_palette,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
)
from features.image.simple_normal_roughness_service import SimpleNormalRoughnessService

try:
    from PySide6.QtCore import QSettings, Qt, QTimer
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLineEdit,
        QMainWindow,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for simple_normal_roughness.") from exc

APP_ID = "simple_normal_roughness"
APP_TITLE = qt_t("simple_normal_roughness.title", "Simple PBR Generator")
APP_SUBTITLE = qt_t("simple_normal_roughness.subtitle", "Generate Normal/Roughness maps from images.")


class SimpleNormalRoughnessWindow(QMainWindow):
    def __init__(self, service: SimpleNormalRoughnessService, app_root: str | Path, targets: list[str] | None = None) -> None:
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
        self.resize(1440, 940)
        self.setMinimumSize(1100, 780)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._apply_compact_styles()
        self._restore_window_state()
        self._bind_actions()

        # Enable Split comparison
        self.preview_list_panel.set_comparative_mode("split")

        if targets:
            self.service.add_inputs(targets)
        self._refresh_parameter_form()
        self._refresh_assets()
        self._runtime_timer.start()

    def _apply_compact_styles(self) -> None:
        m = get_shell_metrics()
        p = get_shell_palette()
        compact_styles = f"""
            QComboBox, QLineEdit {{
                min-height: 30px;
                max-height: 30px;
                padding: 2px 10px;
                border-radius: {m.field_radius - 4}px;
                background: rgba(15, 17, 20, 0.6);
            }}
            #card QFrame#subtlePanel {{
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.05);
                margin-bottom: -6px;
            }}
            QListWidget {{
                background: rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(118, 132, 156, 0.15);
                padding: 4px;
            }}
            QPushButton#pillBtn {{
                background: {p.accent_soft};
                color: {p.text};
                border-radius: 17px;
                padding: 6px 18px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid {p.control_border};
            }}
        """
        self.setStyleSheet(self.styleSheet() + compact_styles)

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
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        
        self.preview_list_panel = PreviewListPanel(
            preview_title=qt_t("pbr.preview", "Map Preview"),
            list_title=qt_t("pbr.inputs", "Input Images"),
        )
        
        self.right_container = QFrame()
        self.right_container.setObjectName("card")
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        right_layout.setSpacing(m.section_gap)

        self.param_panel = FixedParameterPanel(
            title=qt_t("pbr.parameters", "PBR Parameters"),
            description=qt_t("pbr.desc", "Adjust normal strength and roughness contrast."),
        )
        # Hide preset combo as we don't need it for this simple app
        self.param_panel.preset_label.hide()
        self.param_panel.preset_combo.hide()
        
        right_layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportRunPanel(qt_t("pbr.run_panel", "Process & Export"))
        self.export_panel.set_values(
            "", "pbr_", True, False
        )
        self.export_panel.set_expanded(False)
        right_layout.addWidget(self.export_panel, 0)

        self.splitter.addWidget(self.preview_list_panel)
        self.splitter.addWidget(self.right_container)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        
        shell_layout.addWidget(self.splitter, 1)
        
        grip_row = QHBoxLayout()
        grip_row.addStretch(1)
        grip_row.addWidget(build_size_grip())
        shell_layout.addLayout(grip_row)
        root.addWidget(self.window_shell)

    def _bind_actions(self) -> None:
        self.preview_list_panel.add_requested.connect(self._pick_inputs)
        self.preview_list_panel.remove_requested.connect(self._remove_selected_input)
        self.preview_list_panel.clear_requested.connect(self._clear_inputs)
        self.preview_list_panel.selection_changed.connect(self._sync_preview_from_selection)
        self.export_panel.run_requested.connect(self._run_workflow)
        self.export_panel.reveal_requested.connect(self.service.reveal_output_dir)

    def _refresh_parameter_form(self) -> None:
        self.param_panel.clear_fields()
        for definition in self.service.get_ui_definition():
            widget = self._create_param_widget(definition)
            self.param_panel.add_field(str(definition["label"]), widget)

    def _create_param_widget(self, definition: dict[str, object]) -> QWidget:
        key = str(definition["key"])
        kind = str(definition.get("type", "string"))
        value = self.service.state.parameter_values.get(key, definition.get("default"))

        if kind == "choice":
            widget = QComboBox()
            widget.addItems([str(o) for o in definition.get("options", [])])
            widget.setCurrentText(str(value))
            widget.currentTextChanged.connect(lambda t, k=key: self._update_and_preview(k, t))
            return widget
        if kind == "bool":
            widget = QCheckBox()
            widget.setChecked(bool(value))
            widget.stateChanged.connect(lambda s, k=key: self._update_and_preview(k, bool(s)))
            return widget
        
        widget = QLineEdit(str(value))
        widget.textChanged.connect(lambda t, k=key: self._update_and_preview(k, t))
        return widget

    def _update_and_preview(self, key, value):
        self.service.update_parameter(key, value)
        self._refresh_preview()

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images")
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

    def _refresh_assets(self) -> None:
        items = [(a.path.name, str(a.path)) for a in self.service.state.input_assets]
        self.preview_list_panel.set_items(items)
        self.header_surface.asset_count_badge.setText(f"{len(items)} images")
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        path = self.service.state.preview_path
        if not path:
            self.preview_list_panel.set_preview("Select an image", "")
            return
        
        try:
            # Original
            orig_pm = QPixmap(str(path))
            
            # Processed (Normal or Roughness)
            pil_img = self.service.get_processed_preview(path)
            qimg = QImage(pil_img.tobytes(), pil_img.width, pil_img.height, QImage.Format_RGB888)
            proc_pm = QPixmap.fromImage(qimg)
            
            self.preview_list_panel.set_comparative_images(orig_pm, proc_pm)
        except Exception as e:
            self.preview_list_panel.set_preview(f"Error: {e}", str(path))

    def _run_workflow(self) -> None:
        self.service.update_output_options(
            self.export_panel.output_dir_edit.text(),
            self.export_panel.output_prefix_edit.text(),
            self.export_panel.open_folder_checkbox.isChecked(),
            self.export_panel.export_session_checkbox.isChecked(),
        )
        ok, msg, _ = self.service.run_workflow()
        self.export_panel.status_label.setText(msg)

    def _check_runtime_preferences(self) -> None:
        if self._runtime_signature != runtime_settings_signature():
            self._runtime_signature = runtime_settings_signature()
            refresh_runtime_preferences()
            self.setStyleSheet(build_shell_stylesheet())
            self._apply_compact_styles()

    def _restore_window_state(self) -> None:
        geo = self._settings.value("geometry")
        if geo: self.restoreGeometry(geo)

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = SimpleNormalRoughnessWindow(SimpleNormalRoughnessService(), Path(__file__).resolve().parents[3] / APP_ID, targets)
    window.show()
    return app.exec()
