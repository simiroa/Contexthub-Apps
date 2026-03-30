from __future__ import annotations

import sys
from pathlib import Path

from features.comfyui.creative_studio_advanced_service import CreativeStudioAdvancedService
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
        QFileDialog,
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
    raise ImportError("PySide6 is required for creative_studio_advanced.") from exc

APP_ID = "creative_studio_advanced"
APP_TITLE = qt_t("comfyui.creative_studio_advanced.title", "Creative Studio Advanced")
APP_SUBTITLE = qt_t("comfyui.qt_advanced.subtitle", "Compact Qt shell for fast asset staging and parameter control.")


class WorkerThread(QThread):
    finished_with_result = Signal(bool, str, object)

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def run(self) -> None:
        ok, message, payload = self._callback()
        self.finished_with_result.emit(ok, message, payload)


class CreativeStudioAdvancedWindow(QMainWindow):
    def __init__(self, service: CreativeStudioAdvancedService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._run_thread: WorkerThread | None = None
        self._probe_thread: WorkerThread | None = None
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._section_widgets: dict[str, CollapsibleSection] = {}
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1500, 980)
        self.setMinimumSize(1240, 840)
        self.setAcceptDrops(True)
        apply_app_icon(self, self.app_root)

        self._apply_style()
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()
        self._refresh_workflow_selector()
        self._runtime_timer.start()

        if targets:
            self.service.add_inputs(targets)
        self._refresh_input_list()
        self._refresh_preview()

    def _apply_style(self) -> None:
        self.setStyleSheet(build_shell_stylesheet())

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
        self.asset_panel = AssetWorkspacePanel(
            title=qt_t("comfyui.qt_advanced.input_assets", "Input Assets"),
            list_title=qt_t("comfyui.qt_advanced.inputs", "Inputs"),
        )
        self.right_panel = self._build_right_card()
        self.splitter.addWidget(self.asset_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 5)
        self.splitter.setSizes([880, 560])
        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)

        root.addWidget(self.window_shell)

    def _build_right_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        top = QHBoxLayout()
        top.setObjectName("panelTopBar")
        top.setSpacing(14)
        title_box = QVBoxLayout()
        title_box.setSpacing(6)
        section_title = QLabel(qt_t("comfyui.qt_advanced.parameters", "Parameters"))
        section_title.setObjectName("sectionTitle")
        self.workflow_description = QLabel("")
        self.workflow_description.setObjectName("muted")
        self.workflow_description.setWordWrap(True)
        title_box.addWidget(section_title)
        title_box.addWidget(self.workflow_description)
        top.addLayout(title_box, 1)

        preset_box = QVBoxLayout()
        preset_box.setSpacing(6)
        preset_label = QLabel(qt_t("comfyui.qt_advanced.preset", "Preset"))
        preset_label.setObjectName("eyebrow")
        self.workflow_combo = QComboBox()
        self.workflow_combo.setObjectName("presetCombo")
        self.workflow_combo.setMinimumWidth(300)
        self.workflow_combo.setMaximumWidth(340)
        preset_box.addWidget(preset_label)
        preset_box.addWidget(self.workflow_combo)
        top.addLayout(preset_box, 0)
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
        self.asset_panel.add_requested.connect(self._pick_inputs)
        self.asset_panel.preview_requested.connect(self._set_selected_preview)
        self.asset_panel.remove_requested.connect(self._remove_selected_input)
        self.asset_panel.selection_changed.connect(self._sync_preview_from_selection)
        self.asset_panel.files_dropped.connect(self._handle_dropped_inputs)
        self.workflow_combo.currentTextChanged.connect(self._on_workflow_changed)
        self.open_webui_btn.clicked.connect(self._open_webui)
        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.export_panel.export_requested.connect(self._export_session)
        self.export_panel.run_requested.connect(self._run_workflow)
        self.export_panel.toggle_requested.connect(self._toggle_export_details)
        self._start_runtime_probe()

    def _refresh_workflow_selector(self) -> None:
        names = self.service.get_workflow_names()
        self.workflow_combo.blockSignals(True)
        self.workflow_combo.clear()
        self.workflow_combo.addItems(names)
        if self.service.state.workflow_name:
            index = self.workflow_combo.findText(self.service.state.workflow_name)
            if index >= 0:
                self.workflow_combo.setCurrentIndex(index)
        self.workflow_combo.blockSignals(False)
        self._rebuild_parameter_form()

    def _clear_param_layout(self) -> None:
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _rebuild_parameter_form(self) -> None:
        self._clear_param_layout()
        self.workflow_description.setText(self.service.state.workflow_description)
        palette = get_shell_palette()

        sections = {
            "Model": CollapsibleSection(qt_t("comfyui.qt_advanced.section_model", "Model"), expanded=True),
            "Prompt": CollapsibleSection(qt_t("comfyui.qt_advanced.section_prompt", "Prompt"), expanded=True),
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

        for name in ("Model", "Prompt", "Sampling", "Advanced"):
            sections[name].finish()
            self.param_layout.addWidget(sections[name])

        self.param_layout.addStretch(1)
        self.export_panel.status_label.setText(qt_t("comfyui.qt_advanced.workflow_preset_loaded", "Workflow preset loaded."))

    def _section_for_definition(self, key: str, type_name: str) -> str:
        if key in {"ckpt", "model"}:
            return "Model"
        if key in {"prompt", "negative"} or type_name == "text":
            return "Prompt"
        if key in {"steps", "cfg", "sampler", "scheduler", "seed", "batch_size", "resolution"}:
            return "Sampling"
        return "Advanced"

    def _create_param_widget(self, definition):
        kind = definition.type
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
            value_label = QLabel(str(definition.default))
            slider = QSlider(Qt.Horizontal)
            options = definition.options or {}
            slider.setMinimum(int(float(options.get("from", 0))))
            slider.setMaximum(int(float(options.get("to", 100))))
            slider.setValue(int(float(definition.default or options.get("from", 0))))
            slider.valueChanged.connect(
                lambda value, key=definition.key, label=value_label: self._on_slider_changed(key, label, value)
            )
            layout.addWidget(value_label)
            layout.addWidget(slider)
            return widget

        if kind == "checkbox":
            check = QCheckBox(definition.label)
            check.setChecked(bool(definition.default))
            check.toggled.connect(lambda value, key=definition.key: self.service.update_parameter(key, value))
            return check

        if kind == "seed":
            spin = QSpinBox()
            spin.setRange(-1, 2147483647)
            spin.setValue(int(definition.default or -1))
            spin.valueChanged.connect(lambda value, key=definition.key: self.service.update_parameter(key, value))
            return spin

        if kind in {"string", "text"}:
            text = QTextEdit()
            if definition.default:
                text.setPlainText(str(definition.default))
            text.textChanged.connect(lambda key=definition.key, editor=text: self.service.update_parameter(key, editor.toPlainText()))
            return text

        line = QLineEdit()
        if definition.default:
            line.setText(str(definition.default))
        line.textChanged.connect(lambda value, key=definition.key: self.service.update_parameter(key, value))
        return line

    def _on_slider_changed(self, key: str, label: QLabel, value: int) -> None:
        label.setText(str(value))
        self.service.update_parameter(key, value)

    def _pick_inputs(self) -> None:
        paths, _selected = QFileDialog.getOpenFileNames(
            self,
            qt_t("comfyui.qt_advanced.add_input_assets", "Add input assets"),
            "",
            "Media Files (*.png *.jpg *.jpeg *.webp *.bmp *.mp4 *.mov *.wav *.mp3);;All Files (*)",
        )
        if not paths:
            return
        self.service.add_inputs(paths)
        self._refresh_input_list()
        self._refresh_preview()

    def _refresh_input_list(self) -> None:
        self.asset_panel.set_inputs(self.service.state.input_assets)
        self.asset_count_badge.setText(
            qt_t("comfyui.qt_advanced.input_count", "{count} inputs", count=len(self.service.state.input_assets))
        )

    def _sync_preview_from_selection(self) -> None:
        row = self.asset_panel.current_row()
        if row >= 0:
            self.service.set_preview_from_index(row)
            self._refresh_preview()

    def _set_selected_preview(self) -> None:
        row = self.asset_panel.current_row()
        if row >= 0:
            self.service.set_preview_from_index(row)
            self._refresh_preview()

    def _remove_selected_input(self) -> None:
        row = self.asset_panel.current_row()
        if row >= 0:
            self.service.remove_input_at(row)
            self._refresh_input_list()
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        self.asset_panel.set_preview(self.service.state.preview_path)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh_preview()

    def _on_workflow_changed(self, name: str) -> None:
        if name:
            self.service.select_workflow(name)
            self._rebuild_parameter_form()
            self._refresh_status(qt_t("comfyui.qt_advanced.loaded_preset", "Loaded preset: {name}", name=name), "ready")

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
        title = qt_t("comfyui.creative_studio_advanced.title", "Creative Studio Advanced")
        subtitle = qt_t("comfyui.qt_advanced.subtitle", "Compact Qt shell for fast asset staging and parameter control.")
        self.setWindowTitle(title)
        self.setStyleSheet(build_shell_stylesheet())
        self.header_surface.retranslate(title, subtitle)
        self.asset_panel.retranslate(
            qt_t("comfyui.qt_advanced.input_assets", "Input Assets"),
            qt_t("comfyui.qt_advanced.inputs", "Inputs"),
        )
        self.export_panel.retranslate(qt_t("comfyui.qt_panels.export_and_run", "Export And Run"))
        if self._section_widgets:
            self._section_widgets["Model"].set_title(qt_t("comfyui.qt_advanced.section_model", "Model"))
            self._section_widgets["Prompt"].set_title(qt_t("comfyui.qt_advanced.section_prompt", "Prompt"))
            self._section_widgets["Sampling"].set_title(qt_t("comfyui.qt_advanced.section_sampling", "Sampling"))
            self._section_widgets["Advanced"].set_title(qt_t("comfyui.qt_advanced.section_advanced", "Advanced"))
        self._refresh_input_list()
        self._rebuild_parameter_form()

    def _open_webui(self) -> None:
        self._collect_output_options()
        try:
            self.service.open_webui()
            self._refresh_status(qt_t("comfyui.qt_advanced.opened_webui", "Opened ComfyUI WebUI."), "ready")
        except Exception as exc:
            self._refresh_status(str(exc), "error")

    def _reveal_output_dir(self) -> None:
        self._collect_output_options()
        self.service.reveal_output_dir()
        self._refresh_status(qt_t("comfyui.qt_advanced.opened_output_folder", "Opened output folder."), "ready")

    def _export_session(self) -> None:
        self._collect_output_options()
        try:
            path = self.service.export_session()
            self._refresh_status(
                qt_t("comfyui.qt_advanced.exported_session_json", "Exported session JSON to {name}.", name=path.name),
                "ready",
            )
        except Exception as exc:
            self._refresh_status(qt_t("comfyui.qt_advanced.export_failed", "Export failed: {error}", error=exc), "error")

    def _set_busy(self, busy: bool, label: str | None = None) -> None:
        self.export_panel.run_btn.setEnabled(not busy)
        self.export_panel.export_btn.setEnabled(not busy)
        self.open_webui_btn.setEnabled(not busy)
        busy_label = label or qt_t("comfyui.qt_advanced.run_workflow", "Run Workflow")
        self.export_panel.run_btn.setText(busy_label if busy else qt_t("comfyui.qt_panels.run", "Run"))

    def _run_workflow(self) -> None:
        self._collect_output_options()
        self._set_busy(True, qt_t("comfyui.qt_advanced.running", "..."))
        self._run_thread = WorkerThread(self.service.run_workflow)
        self._run_thread.finished_with_result.connect(self._on_run_finished)
        self._run_thread.start()

    def _on_run_finished(self, ok: bool, message: str, payload: object) -> None:
        self._set_busy(False)
        self._refresh_status(message, "ready" if ok else "warning")
        if payload and isinstance(payload, Path):
            self.export_panel.status_label.setText(
                qt_t("comfyui.qt_advanced.saved_path", "{message}\nSaved: {path}", message=message, path=payload)
            )
            if payload.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                self.service.state.preview_path = payload
                self._refresh_preview()
        if ok and self.export_panel.open_folder_checkbox.isChecked():
            self.service.reveal_output_dir()

    def _handle_dropped_inputs(self, paths: list[str]) -> None:
        self.service.add_inputs(paths)
        self._refresh_input_list()
        self._refresh_preview()
        self._refresh_status(qt_t("comfyui.qt_advanced.added_items", "Added {count} item(s).", count=len(paths)), "ready")

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if paths:
                self._handle_dropped_inputs(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _start_runtime_probe(self) -> None:
        self._refresh_status(qt_t("comfyui.qt_advanced.checking_runtime", "Checking ComfyUI runtime..."), "warning")
        self._probe_thread = WorkerThread(self.service.probe_runtime)
        self._probe_thread.finished_with_result.connect(self._on_probe_finished)
        self._probe_thread.start()

    def _on_probe_finished(self, _ok: bool, message: str, _payload: object) -> None:
        level = "ready" if "Connected" in message else "warning"
        if "failed" in message.lower():
            level = "error"
        self._refresh_status(message, level)

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
    window = CreativeStudioAdvancedWindow(CreativeStudioAdvancedService(), app_root, targets or [])
    window.show()
    app.exec()
