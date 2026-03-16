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
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
)
from features.image.resize_power_of_2_service import ResizePowerOf2Service

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
    raise ImportError("PySide6 is required for resize_power_of_2.") from exc

APP_ID = "resize_power_of_2"
APP_TITLE = qt_t("resize_power_of_2.title", "POT Resizer")
APP_SUBTITLE = qt_t("resize_power_of_2.subtitle", "Resize images to Power of 2 dimensions.")


class ResizePowerOf2Window(QMainWindow):
    def __init__(self, service: ResizePowerOf2Service, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1200, 860)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._apply_compact_styles()
        self._restore_window_state()
        self._bind_actions()

        # Enable Side-by-Side comparison
        self.preview_list_panel.set_comparative_mode("side")

        if targets:
            self.service.add_inputs(targets)
        self._refresh_parameter_form()
        self._refresh_assets()
        self._runtime_timer.start()

    def _apply_compact_styles(self) -> None:
        m = get_shell_metrics()
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
        """
        self.setStyleSheet(self.styleSheet() + compact_styles)

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        
        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.preview_list_panel = PreviewListPanel(preview_title="Preview", list_title="Input Gallery")
        
        self.right_container = QFrame()
        self.right_container.setObjectName("card")
        right_layout = QVBoxLayout(self.right_container)
        
        self.param_panel = FixedParameterPanel(title="Resize Settings")
        self.param_panel.preset_label.hide()
        self.param_panel.preset_combo.hide()
        right_layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportRunPanel("Execution")
        self.export_panel.set_values("", "resized_", True, False)
        self.export_panel.set_expanded(False)
        right_layout.addWidget(self.export_panel, 0)

        self.splitter.addWidget(self.preview_list_panel)
        self.splitter.addWidget(self.right_container)
        self.splitter.setStretchFactor(0, 6)
        self.splitter.setStretchFactor(1, 4)
        
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
        for d in self.service.get_ui_definition():
            widget = self._create_param_widget(d)
            self.param_panel.add_field(str(d["label"]), widget)

    def _create_param_widget(self, d: dict) -> QWidget:
        key, kind, value = str(d["key"]), str(d.get("type", "string")), self.service.state.parameter_values.get(str(d["key"]), d.get("default"))
        if kind == "choice":
            w = QComboBox()
            w.addItems([str(o) for o in d.get("options", [])])
            w.setCurrentText(str(value))
            w.currentTextChanged.connect(lambda t, k=key: self.service.update_parameter(k, t))
            return w
        if kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
            w.stateChanged.connect(lambda s, k=key: self.service.update_parameter(k, bool(s)))
            return w
        w = QLineEdit(str(value))
        w.textChanged.connect(lambda t, k=key: self.service.update_parameter(k, t))
        return w

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
            self.preview_list_panel.set_preview("Select image", "")
            return
        
        try:
            # Original
            orig_pm = QPixmap(str(path))
            
            # Processed (Standard resize preview)
            # For resize app, we'll just show the same image or a roughly resized version if possible
            # Here, we'll just use the same pixmap for demo, or we could actually run a quick resize
            self.preview_list_panel.set_comparative_images(orig_pm, orig_pm)
        except Exception as e:
            self.preview_list_panel.set_preview(f"Error: {e}", str(path))

    def _run_workflow(self) -> None:
        self.service.update_output_options(self.export_panel.output_dir_edit.text(), self.export_panel.output_prefix_edit.text(), self.export_panel.open_folder_checkbox.isChecked(), self.export_panel.export_session_json.isChecked())
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
    window = ResizePowerOf2Window(ResizePowerOf2Service(), Path(__file__).resolve().parents[3] / APP_ID, targets)
    window.show()
    return app.exec()
