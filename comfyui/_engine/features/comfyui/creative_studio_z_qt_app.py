from __future__ import annotations

import sys
from pathlib import Path

from features.comfyui.creative_studio_z_service import CreativeStudioZService
from contexthub.ui.qt.panels import AssetWorkspacePanel, ExportFoldoutPanel
from contexthub.ui.qt.shell import (
    apply_app_icon,
    CollapsibleSection,
    HeaderSurface,
    attach_size_grip,
    build_shell_stylesheet,
    get_shell_palette,
    set_badge_role,
    set_surface_role,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
)

try:
    from PySide6.QtCore import QSettings, QThread, Qt, QTimer, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QScrollArea,
        QSlider,
        QSpinBox,
        QTextEdit,
        QVBoxLayout,
        QWidget,
        QSplitter,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for creative_studio_z.") from exc

APP_ID = "creative_studio_z"
APP_TITLE = qt_t("comfyui.creative_studio_z.title", "Creative Studio Z")
APP_SUBTITLE = qt_t("comfyui.qt_z.subtitle", "Fast settings and tools for Z-Turbo ideation.")


class WorkerThread(QThread):
    finished_with_result = Signal(bool, str, object)

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def run(self) -> None:
        ok, message, payload = self._callback()
        self.finished_with_result.emit(ok, message, payload)


class CreativeStudioZWindow(QMainWindow):
    def __init__(self, service: CreativeStudioZService, app_root: str | Path) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._run_thread: WorkerThread | None = None
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._section_widgets: dict[str, CollapsibleSection] = {}
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1420, 920)
        self.setMinimumSize(1180, 780)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()
        self._rebuild_parameter_form()
        self._refresh_recent_files()
        self._refresh_preview()
        self._refresh_status(qt_t("comfyui.qt_panels.ready", "Ready"), "ready")
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(10, 10, 10, 10)
        shell_layout.setSpacing(12)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root, show_webui=True)
        self.header_surface.set_header_visibility(show_subtitle=True, show_asset_count=True, show_runtime_status=True)
        self.asset_count_badge = self.header_surface.asset_count_badge
        self.runtime_status_badge = self.header_surface.runtime_status_badge
        self.open_webui_btn = self.header_surface.open_webui_btn
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        self.preview_panel = AssetWorkspacePanel(
            title=qt_t("comfyui.qt_z.result_preview", "Result Preview"),
            list_title=qt_t("comfyui.qt_z.recent_files", "Recent Files"),
        )
        self.preview_panel.add_inputs_btn.setText("📁")
        self.preview_panel.add_inputs_btn.setToolTip(qt_t("comfyui.qt_panels.reveal_output_folder", "Reveal output folder"))
        self.preview_panel.set_preview_btn.setText("👁")
        self.preview_panel.set_preview_btn.setToolTip(qt_t("comfyui.qt_z.focus_selected_result", "Focus selected result"))
        self.preview_panel.clear_input_btn.setText("✕")
        self.preview_panel.clear_input_btn.setToolTip(qt_t("comfyui.qt_z.remove_selected_recent_file", "Remove selected recent file"))
        self.right_panel = self._build_right_panel()
        self.splitter.addWidget(self.preview_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 6)
        self.splitter.setStretchFactor(1, 5)
        self.splitter.setSizes([760, 620])
        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _build_right_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel(qt_t("comfyui.qt_z.quick_settings", "Quick Settings"))
        title.setObjectName("sectionTitle")
        self.description_label = QLabel(self.service.get_description())
        self.description_label.setObjectName("muted")
        self.description_label.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(self.description_label)
        top.addLayout(title_box, 1)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_body = QWidget()
        scroll_body.setObjectName("paramScrollBody")
        set_surface_role(scroll.viewport(), "content")
        set_surface_role(scroll_body, "content")
        self.param_layout = QVBoxLayout(scroll_body)
        self.param_layout.setContentsMargins(0, 0, 0, 0)
        self.param_layout.setSpacing(10)
        scroll.setWidget(scroll_body)
        scroll.viewport().setObjectName("paramScrollViewport")
        layout.addWidget(scroll, 1)

        self.export_panel = ExportFoldoutPanel(qt_t("comfyui.qt_panels.export_and_run", "Export And Run"))
        self.export_panel.set_values(
            str(self.service.state.output_options.output_dir),
            self.service.state.output_options.file_prefix,
            self.service.state.output_options.open_folder_after_run,
            self.service.state.output_options.export_session_json,
        )
        self.export_panel.set_expanded(False)
        layout.addWidget(self.export_panel)
        return card

    def _bind_actions(self) -> None:
        self.preview_panel.add_requested.connect(self._reveal_output_dir)
        self.preview_panel.preview_requested.connect(self._focus_selected_recent)
        self.preview_panel.remove_requested.connect(self._remove_selected_recent)
        self.preview_panel.selection_changed.connect(self._focus_selected_recent)
        self.open_webui_btn.clicked.connect(self._open_webui)
        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.export_panel.export_requested.connect(self._export_session)
        self.export_panel.run_requested.connect(self._run_workflow)
        self.export_panel.toggle_requested.connect(self._toggle_export_details)

    def _rebuild_parameter_form(self) -> None:
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sections = {
            "Prompt": CollapsibleSection(qt_t("comfyui.qt_advanced.section_prompt", "Prompt"), expanded=True),
            "Quick": CollapsibleSection(qt_t("comfyui.qt_z.quick_settings", "Quick Settings"), expanded=True),
            "Sampling": CollapsibleSection(qt_t("comfyui.qt_advanced.section_sampling", "Sampling"), expanded=True),
            "Advanced": CollapsibleSection(qt_t("comfyui.qt_advanced.section_advanced", "Advanced"), expanded=False),
        }
        self._section_widgets = sections

        for definition in self.service.get_ui_definition():
            group = QFrame()
            group.setObjectName("subtlePanel")
            inner = QVBoxLayout(group)
            inner.setContentsMargins(10, 8, 10, 8)
            inner.setSpacing(4)
            title = QLabel(definition.label)
            title.setObjectName("eyebrow")
            inner.addWidget(title)
            inner.addWidget(self._create_param_widget(definition))
            sections[self._section_for_definition(definition.key, definition.type)].add_widget(group)

        for name in ("Prompt", "Quick", "Sampling", "Advanced"):
            sections[name].finish()
            self.param_layout.addWidget(sections[name])
        self.param_layout.addStretch(1)

    def _section_for_definition(self, key: str, type_name: str) -> str:
        if key == "prompt" or type_name == "text":
            return "Prompt"
        if key in {"resolution", "upscale", "rembg", "save_ico"}:
            return "Quick"
        if key in {"steps", "cfg", "seed", "batch_size"}:
            return "Sampling"
        return "Advanced"

    def _create_param_widget(self, definition):
        kind = definition.type
        if definition.key == "resolution":
            combo = QComboBox()
            combo.addItems(["1024x1024", "896x1152", "1152x896", "768x768"])
            combo.setCurrentText(self.service.state.parameter_values["resolution"])
            combo.currentTextChanged.connect(lambda value: self.service.update_parameter("resolution", value))
            return combo

        if kind in {"combo", "ckpt", "aspect"}:
            combo = QComboBox()
            combo.addItems([str(option) for option in (definition.options or [])])
            if definition.default is not None:
                combo.setCurrentText(str(definition.default))
            combo.currentTextChanged.connect(lambda value, key=definition.key: self.service.update_parameter(key, value))
            return combo

        if kind == "slider":
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            value_label = QLabel(str(self.service.state.parameter_values.get(definition.key, definition.default)))
            slider = QSlider(Qt.Horizontal)
            options = definition.options or {}
            slider.setMinimum(int(float(options.get("from", 0))))
            slider.setMaximum(int(float(options.get("to", 100))))
            slider.setValue(int(float(self.service.state.parameter_values.get(definition.key, definition.default or 0))))
            slider.valueChanged.connect(lambda value, key=definition.key, label=value_label: self._on_slider_changed(key, label, value))
            layout.addWidget(value_label)
            layout.addWidget(slider)
            return widget

        if kind == "checkbox":
            check = QCheckBox(definition.label)
            check.setChecked(bool(self.service.state.parameter_values.get(definition.key, definition.default)))
            check.toggled.connect(lambda value, key=definition.key: self.service.update_parameter(key, value))
            return check

        if kind in {"string", "text"}:
            text = QTextEdit()
            default = self.service.state.parameter_values.get(definition.key, definition.default or "")
            text.setPlainText(str(default))
            text.textChanged.connect(lambda key=definition.key, editor=text: self.service.update_parameter(key, editor.toPlainText()))
            return text

        if kind == "seed":
            spin = QSpinBox()
            spin.setRange(-1, 2147483647)
            spin.setValue(int(self.service.state.parameter_values.get(definition.key, -1)))
            spin.valueChanged.connect(lambda value, key=definition.key: self.service.update_parameter(key, value))
            return spin

        line = QLineEdit()
        default = self.service.state.parameter_values.get(definition.key, definition.default or "")
        line.setText(str(default))
        line.textChanged.connect(lambda value, key=definition.key: self.service.update_parameter(key, value))
        return line

    def _on_slider_changed(self, key: str, label: QLabel, value: int) -> None:
        label.setText(str(value))
        self.service.update_parameter(key, value)

    def _refresh_recent_files(self) -> None:
        assets = [type("RecentFile", (), {"path": path, "kind": "image" if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"} else "file"}) for path in self.service.state.recent_files]
        self.preview_panel.set_inputs(assets)
        self.asset_count_badge.setText(qt_t("comfyui.qt_z.file_count", "{count} files", count=len(self.service.state.recent_files)))

    def _refresh_preview(self) -> None:
        self.preview_panel.set_preview(self.service.state.preview_path)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh_preview()

    def _focus_selected_recent(self) -> None:
        row = self.preview_panel.current_row()
        if 0 <= row < len(self.service.state.recent_files):
            self.service.state.preview_path = self.service.state.recent_files[row]
            self._refresh_preview()

    def _remove_selected_recent(self) -> None:
        row = self.preview_panel.current_row()
        if row >= 0:
            self.service.clear_recent_file(row)
            self._refresh_recent_files()
            self._refresh_preview()

    def _collect_output_options(self) -> None:
        self.service.update_output_options(
            self.export_panel.output_dir_edit.text(),
            self.export_panel.output_prefix_edit.text(),
            self.export_panel.open_folder_checkbox.isChecked(),
            self.export_panel.export_session_checkbox.isChecked(),
        )
        self.export_panel.refresh_summary()

    def _toggle_export_details(self) -> None:
        self.export_panel.set_expanded(not self.export_panel.details.isVisible())

    def _refresh_status(self, text: str, level: str) -> None:
        self.runtime_status_badge.setText(text)
        tone = {"ready": "success", "warning": "warning", "error": "error"}.get(level, "accent")
        set_badge_role(self.runtime_status_badge, "status", tone)
        self.export_panel.status_label.setText(text)

    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self._apply_runtime_preferences()

    def _apply_runtime_preferences(self) -> None:
        title = qt_t("comfyui.creative_studio_z.title", "Creative Studio Z")
        subtitle = qt_t("comfyui.qt_z.subtitle", "Fast settings and tools for Z-Turbo ideation.")
        self.setWindowTitle(title)
        self.setStyleSheet(build_shell_stylesheet())
        self.header_surface.retranslate(title, subtitle)
        self.preview_panel.retranslate(
            qt_t("comfyui.qt_z.result_preview", "Result Preview"),
            qt_t("comfyui.qt_z.recent_files", "Recent Files"),
        )
        self.preview_panel.add_inputs_btn.setToolTip(qt_t("comfyui.qt_panels.reveal_output_folder", "Reveal output folder"))
        self.preview_panel.set_preview_btn.setToolTip(qt_t("comfyui.qt_z.focus_selected_result", "Focus selected result"))
        self.preview_panel.clear_input_btn.setToolTip(qt_t("comfyui.qt_z.remove_selected_recent_file", "Remove selected recent file"))
        self.export_panel.retranslate(qt_t("comfyui.qt_panels.export_and_run", "Export And Run"))
        if self._section_widgets:
            self._section_widgets["Prompt"].set_title(qt_t("comfyui.qt_advanced.section_prompt", "Prompt"))
            self._section_widgets["Quick"].set_title(qt_t("comfyui.qt_z.quick_settings", "Quick Settings"))
            self._section_widgets["Sampling"].set_title(qt_t("comfyui.qt_advanced.section_sampling", "Sampling"))
            self._section_widgets["Advanced"].set_title(qt_t("comfyui.qt_advanced.section_advanced", "Advanced"))
        self._rebuild_parameter_form()
        self._refresh_recent_files()

    def _reveal_output_dir(self) -> None:
        self._collect_output_options()
        self.service.reveal_output_dir()
        self._refresh_status(qt_t("comfyui.qt_advanced.opened_output_folder", "Opened output folder."), "ready")

    def _open_webui(self) -> None:
        self._collect_output_options()
        self.service.open_webui()
        self._refresh_status(qt_t("comfyui.qt_advanced.opened_webui", "Opened ComfyUI WebUI."), "ready")

    def _export_session(self) -> None:
        self._collect_output_options()
        path = self.service.export_session()
        self._refresh_recent_files()
        self._refresh_preview()
        self._refresh_status(
            qt_t("comfyui.qt_advanced.exported_session_json", "Exported session JSON to {name}.", name=path.name),
            "ready",
        )

    def _set_busy(self, busy: bool, label: str | None = None) -> None:
        self.export_panel.run_btn.setEnabled(not busy)
        self.export_panel.export_btn.setEnabled(not busy)
        busy_label = label or qt_t("comfyui.qt_panels.run", "Run")
        self.export_panel.run_btn.setText(busy_label if busy else qt_t("comfyui.qt_panels.run", "Run"))

    def _run_workflow(self) -> None:
        self._collect_output_options()
        self._set_busy(True, qt_t("comfyui.qt_z.running", "..."))
        self._run_thread = WorkerThread(self.service.run_workflow)
        self._run_thread.finished_with_result.connect(self._on_run_finished)
        self._run_thread.start()

    def _on_run_finished(self, ok: bool, message: str, payload: object) -> None:
        self._set_busy(False)
        self._refresh_recent_files()
        self._refresh_preview()
        self._refresh_status(message, "ready" if ok else "warning")
        self.service.state.status_text = message
        self.service.state.status_level = "ready" if ok else "warning"
        if payload and isinstance(payload, Path):
            self.export_panel.status_label.setText(
                qt_t("comfyui.qt_advanced.saved_path", "{message}\nSaved: {path}", message=message, path=payload)
            )

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        window_state = self._settings.value("windowState")
        if window_state == "maximized":
            self.showMaximized()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("windowState", "maximized" if self.isMaximized() else "normal")
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app_root = Path(__file__).resolve().parents[3] / APP_ID
    window = CreativeStudioZWindow(CreativeStudioZService(), app_root)
    window.show()
    app.exec()
