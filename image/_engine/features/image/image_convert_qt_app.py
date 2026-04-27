from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.panels import ExportRunPanel, FixedParameterPanel, PreviewListPanel
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
from features.image.image_convert_service import ImageConvertService

try:
    from PySide6.QtCore import QSettings, Qt, QTimer
    from PySide6.QtGui import QImage, QPixmap
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
    raise ImportError("PySide6 is required for image_convert.") from exc

APP_ID = "image_convert"
APP_TITLE = qt_t("image_convert.title", "Image Converter")
APP_SUBTITLE = qt_t("image_convert.subtitle", "Batch convert images efficiently.")


class ImageConvertWindow(QMainWindow):
    def __init__(self, service: ImageConvertService, app_root: str | Path, targets: list[str] | None = None) -> None:
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
        self.resize(1280, 840)
        self.setMinimumSize(1000, 700)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._apply_compact_styles()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs(targets)
        self._refresh_presets()
        self._refresh_parameter_form()
        self._refresh_assets()
        self._runtime_timer.start()

    def _apply_compact_styles(self) -> None:
        m = get_shell_metrics()
        p = get_shell_palette()
        compact_styles = f"""
            QComboBox, QLineEdit {{{{
                min-height: 30px;
                max-height: 30px;
                padding: 2px 10px;
                border-radius: {m.field_radius - 4}px;
                background: {p.field_bg};
            }}}}
            QGroupBox#exportRunPanel QLineEdit {{{{
                min-height: 26px;
                max-height: 26px;
            }}}}
            #card QFrame#subtlePanel {{{{
                background: transparent;
                border: 1px solid {p.control_border};
                margin-bottom: -6px;
            }}}}
            QLabel#eyebrow {{
                margin-bottom: -2px;
            }}
            /* Finishing for Gallery */
            QListWidget {{
                background: {p.field_bg};
                border: 1px solid {p.control_border};
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                margin-bottom: 2px;
                border-radius: 8px;
            }}
            QListWidget::item:hover {{
                background: {p.button_hover};
            }}
            /* Pill Button Style */
            QPushButton[buttonRole="pill"] {{
                background: {p.accent_soft};
                color: {p.text};
                border-radius: 17px;
                padding: 6px 18px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid {p.control_border};
            }}
            QPushButton[buttonRole="pill"]:hover {{
                background: {p.accent};
                color: {p.accent_text};
                border-color: {p.accent};
            }}
        """
        self.setStyleSheet(self.styleSheet() + compact_styles)
        self.param_panel.description_label.setStyleSheet("margin-bottom: 2px; font-size: 12px;")
        self.export_panel.setStyleSheet(
            self.export_panel.styleSheet() + 
            "QCheckBox { font-size: 11px; padding: 1px; } QLabel { font-size: 11px; }"
        )

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
        self.header_surface.set_header_visibility(
            show_subtitle=False,
            show_asset_count=True,
            show_runtime_status=False,
        )
        self.asset_count_badge = self.header_surface.asset_count_badge
        self.runtime_status_badge = self.header_surface.runtime_status_badge
        self.header_surface.open_webui_btn.hide()
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        self.left_panel = self._build_left_panel()
        self.right_panel = self._build_right_panel()
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _build_left_panel(self) -> PreviewListPanel:
        panel = PreviewListPanel(
            preview_title=qt_t("image_convert.preview", "Preview"),
            list_title=qt_t("image_convert.input_list", "Input Gallery"),
            list_hint=qt_t("image_convert.list_hint", "Select an image to preview."),
        )
        self.preview_list_panel = panel
        return panel

    def _build_right_panel(self) -> QFrame:
        m = get_shell_metrics()

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(max(8, m.section_gap - 2))

        self.param_panel = FixedParameterPanel(
            title=qt_t("image_convert.parameters", "Settings"),
            description=qt_t("image_convert.settings_desc", "Configure conversion options."),
            preset_label=qt_t("image_convert.preset", "Workflow"),
        )
        self.workflow_description = self.param_panel.description_label
        self.workflow_combo = self.param_panel.preset_combo
        layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportRunPanel(qt_t("image_convert.run", "Convert Now"))
        self.export_panel.set_values(
            str(self.service.state.output_options.output_dir),
            self.service.state.output_options.file_prefix,
            self.service.state.output_options.open_folder_after_run,
            self.service.state.output_options.export_session_json,
        )
        self.export_panel.set_expanded(False)
        layout.addWidget(self.export_panel, 0)
        return card

    def _bind_actions(self) -> None:
        self.preview_list_panel.add_requested.connect(self._pick_inputs)
        self.preview_list_panel.remove_requested.connect(self._remove_selected_input)
        self.preview_list_panel.clear_requested.connect(self._clear_inputs)
        self.preview_list_panel.selection_changed.connect(self._sync_preview_from_selection)
        self.workflow_combo.currentTextChanged.connect(self._on_workflow_changed)
        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.export_panel.export_requested.connect(self._export_session)
        self.export_panel.run_requested.connect(self._run_conversion)
        self.export_panel.toggle_requested.connect(self._toggle_export_details)

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

    def _clear_form_body(self) -> None:
        self.param_panel.clear_fields()
        self._field_widgets.clear()

    def _refresh_parameter_form(self) -> None:
        self._clear_form_body()
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

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, APP_TITLE, "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.ico *.exr)")
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

    def _on_workflow_changed(self, name: str) -> None:
        if not name:
            return
        self.service.select_workflow(name)
        self._refresh_parameter_form()

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
        self.asset_count_badge.setText(qt_t("image_convert.asset_count", "{count} images", count=len(self.service.state.input_assets)))
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        preview_path = self.service.service.state.preview_path if hasattr(self.service, "service") else self.service.state.preview_path
        label = self.preview_list_panel.preview_label
        meta = self.preview_list_panel.preview_meta

        if preview_path is None or not preview_path.exists():
            self.preview_list_panel.set_preview(qt_t("image_convert.preview_empty", "Select an image to preview."), "")
            label.setPixmap(QPixmap())
            return

        # Handle images
        if preview_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            image = QImage(str(preview_path))
            if not image.isNull():
                pixmap = QPixmap.fromImage(image).scaled(
                    label.size() if label.width() > 0 else (800, 600),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                label.setPixmap(pixmap)
                label.setText("")
                meta.setText(str(preview_path))
                return

        # Fallback or Non-supported preview types (like EXR, which QImage might not support without plugins)
        self.preview_list_panel.set_preview(preview_path.name, str(preview_path))
        label.setPixmap(QPixmap())


    def _reveal_output_dir(self) -> None:
        self._sync_output_options()
        self.service.reveal_output_dir()

    def _export_session(self) -> None:
        self._sync_output_options()
        path = self.service.export_session()
        self.export_panel.status_label.setText(f"Session saved: {path.name}")

    def _run_conversion(self) -> None:
        if not self.service.state.input_assets:
            return
            
        self._sync_output_options()
        button = getattr(self.export_panel, "run_button", None) or getattr(self.export_panel, "run_btn", None)
        if button is not None:
            button.setEnabled(False)
        self.export_panel.status_label.setText("Starting...")
        
        def on_progress(f, c, t):
            QTimer.singleShot(0, lambda: self.export_panel.status_label.setText(f"Converting: {c}/{t} ({int(f*100)}%)"))
            
        def on_complete(count, errors):
            def _ui():
                button = getattr(self.export_panel, "run_button", None) or getattr(self.export_panel, "run_btn", None)
                if button is not None:
                    button.setEnabled(True)
                if errors:
                    self.export_panel.status_label.setText(f"Done: {count} success, {len(errors)} errors.")
                else:
                    self.export_panel.status_label.setText(f"Success: {count} images converted.")
                if self.service.state.output_options.open_folder_after_run:
                    self.service.reveal_output_dir()
            QTimer.singleShot(0, _ui)

        self.service.run_workflow(on_progress, on_complete)

    def _toggle_export_details(self) -> None:
        self.export_panel.set_expanded(not self.export_panel.details.isVisible())

    def _sync_output_options(self) -> None:
        self.service.update_output_options(
            self.export_panel.output_dir_edit.text(),
            self.export_panel.output_prefix_edit.text(),
            self.export_panel.open_folder_checkbox.isChecked(),
            self.export_panel.export_session_checkbox.isChecked(),
        )
        self.export_panel.refresh_summary()

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
    app_root = Path(__file__).resolve().parents[3] / "image" / "image_convert"
    window = ImageConvertWindow(ImageConvertService(), app_root, targets)
    window.show()
    return app.exec()
