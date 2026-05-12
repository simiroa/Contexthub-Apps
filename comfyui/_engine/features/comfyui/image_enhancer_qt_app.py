from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.panels import ExportFoldoutPanel
from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
    set_surface_role,
)
from features.comfyui.image_enhancer_service import ImageEnhancerService
from features.comfyui.image_enhancer_state import WORKFLOW_CHOICES
from features.comfyui.inpainting_canvas import InpaintingCanvas

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
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSlider,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for image_enhancer.") from exc


APP_ID = "image_enhancer"
APP_TITLE = qt_t("image_enhancer.title", "AI Image Enhancer")
APP_SUBTITLE = qt_t(
    "image_enhancer.subtitle",
    "Painted masks, repair passes, and layered ComfyUI enhancement",
)


class ImageEnhancerWindow(QMainWindow):
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, service: ImageEnhancerService, app_root: str | Path, targets: list[str] | None = None) -> None:
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
        self.resize(1540, 980)
        self.setMinimumSize(1280, 780)
        self.setAcceptDrops(True)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs(targets)
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

        self.left_card = self._build_left_card()
        self.right_card = self._build_right_card()
        self.splitter.addWidget(self.left_card)
        self.splitter.addWidget(self.right_card)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 5)
        self.splitter.setSizes([920, 620])
        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _build_left_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.load_btn = QPushButton(qt_t("image_enhancer.load", "Load Images"))
        self.load_btn.setProperty("buttonRole", "pill")
        self.save_mask_btn = QPushButton(qt_t("image_enhancer.save_mask", "Save Mask"))
        self.save_mask_btn.setProperty("buttonRole", "pill")
        self.clear_mask_btn = QPushButton(qt_t("image_enhancer.clear_mask", "Clear Mask"))
        self.clear_mask_btn.setProperty("buttonRole", "pill")
        self.undo_btn = QPushButton(qt_t("image_enhancer.undo", "Undo"))
        self.redo_btn = QPushButton(qt_t("image_enhancer.redo", "Redo"))
        self.fit_btn = QPushButton(qt_t("image_enhancer.fit", "Fit"))
        self.open_workflows_btn = QPushButton(qt_t("image_enhancer.open_workflows", "Open workflows folder"))
        for btn in (self.load_btn, self.save_mask_btn, self.clear_mask_btn, self.undo_btn, self.redo_btn, self.fit_btn):
            btn.setProperty("buttonRole", "pill")
        top.addWidget(self.load_btn, 1)
        top.addWidget(self.save_mask_btn)
        top.addWidget(self.clear_mask_btn)
        top.addWidget(self.undo_btn)
        top.addWidget(self.redo_btn)
        top.addWidget(self.fit_btn)
        layout.addLayout(top)

        status_strip = QFrame()
        status_strip.setObjectName("subtlePanel")
        status_layout = QHBoxLayout(status_strip)
        status_layout.setContentsMargins(10, 8, 10, 8)
        status_layout.setSpacing(12)
        self.selected_input_label = QLabel(qt_t("image_enhancer.active_input", "No input selected"))
        self.selected_input_label.setObjectName("summaryText")
        self.selected_input_label.setWordWrap(True)
        self.mask_status_label = QLabel(qt_t("image_enhancer.mask_status", "Mask: none"))
        self.mask_status_label.setObjectName("muted")
        self.mask_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_layout.addWidget(self.selected_input_label, 1)
        status_layout.addWidget(self.mask_status_label, 0)
        layout.addWidget(status_strip)

        body = QHBoxLayout()
        body.setSpacing(12)

        input_panel = QFrame()
        input_panel.setObjectName("subtlePanel")
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(8)
        input_title = QLabel(qt_t("image_enhancer.inputs", "Inputs"))
        input_title.setObjectName("eyebrow")
        input_layout.addWidget(input_title)
        self.input_list = QListWidget()
        self.input_list.setMinimumWidth(260)
        self.input_list.setAlternatingRowColors(True)
        input_layout.addWidget(self.input_list, 1)
        body.addWidget(input_panel, 0)

        canvas_panel = QFrame()
        canvas_panel.setObjectName("subtlePanel")
        canvas_layout = QVBoxLayout(canvas_panel)
        canvas_layout.setContentsMargins(10, 10, 10, 10)
        canvas_layout.setSpacing(8)
        self.canvas = InpaintingCanvas()
        self.canvas.setMinimumHeight(520)
        canvas_layout.addWidget(self.canvas, 1)
        self.canvas_status = QLabel(qt_t("image_enhancer.canvas_hint", "Paint the mask on the active image."))
        self.canvas_status.setObjectName("summaryText")
        self.canvas_status.setWordWrap(True)
        canvas_layout.addWidget(self.canvas_status)
        body.addWidget(canvas_panel, 1)

        layout.addLayout(body, 1)
        return card

    def _build_right_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(12)
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel(qt_t("image_enhancer.layers", "Layers"))
        title.setObjectName("sectionTitle")
        self.layers_summary = QLabel("")
        self.layers_summary.setObjectName("muted")
        self.layers_summary.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(self.layers_summary)
        top.addLayout(title_box, 1)

        top.addWidget(self.open_workflows_btn, 0)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_body = QWidget()
        scroll_body.setObjectName("paramScrollBody")
        set_surface_role(scroll.viewport(), "content")
        set_surface_role(scroll_body, "content")
        self.right_scroll_body = scroll_body
        self.right_scroll_viewport = scroll.viewport()
        self.right_scroll_viewport.setObjectName("paramScrollViewport")
        self.right_scroll_viewport.setAttribute(Qt.WA_StyledBackground, True)
        self.right_scroll_body = scroll_body
        self.right_layout = QVBoxLayout(scroll_body)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(12)
        scroll.setWidget(scroll_body)
        layout.addWidget(scroll, 1)

        self.workflow_card = QFrame()
        self.workflow_card.setObjectName("subtlePanel")
        workflow_layout = QVBoxLayout(self.workflow_card)
        workflow_layout.setContentsMargins(12, 12, 12, 12)
        workflow_layout.setSpacing(8)
        workflow_title = QLabel(qt_t("image_enhancer.workflow_stack", "Processing stack"))
        workflow_title.setObjectName("eyebrow")
        workflow_layout.addWidget(workflow_title)
        workflow_hint = QLabel(qt_t("image_enhancer.workflow_hint", "Top to bottom. Disable a layer to skip it."))
        workflow_hint.setObjectName("muted")
        workflow_hint.setWordWrap(True)
        workflow_layout.addWidget(workflow_hint)
        self.layer_list = QListWidget()
        self.layer_list.setMinimumHeight(140)
        workflow_layout.addWidget(self.layer_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.add_layer_btn = QPushButton(qt_t("image_enhancer.add_layer", "Add"))
        self.duplicate_layer_btn = QPushButton(qt_t("image_enhancer.dup_layer", "Duplicate"))
        self.remove_layer_btn = QPushButton(qt_t("image_enhancer.remove_layer", "Remove"))
        self.layer_up_btn = QPushButton(qt_t("image_enhancer.layer_up", "Up"))
        self.layer_down_btn = QPushButton(qt_t("image_enhancer.layer_down", "Down"))
        for btn in (self.add_layer_btn, self.duplicate_layer_btn, self.remove_layer_btn, self.layer_up_btn, self.layer_down_btn):
            btn.setProperty("buttonRole", "pill")
            btn_row.addWidget(btn, 1)
        workflow_layout.addLayout(btn_row)
        self.right_layout.addWidget(self.workflow_card)

        self.layer_detail_card = QFrame()
        self.layer_detail_card.setObjectName("subtlePanel")
        detail_layout = QVBoxLayout(self.layer_detail_card)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(8)

        self.layer_name_edit = QLineEdit()
        self.layer_enabled_check = QCheckBox(qt_t("image_enhancer.layer_enabled", "Enabled"))
        self.layer_use_mask_check = QCheckBox(qt_t("image_enhancer.layer_use_mask", "Use mask"))
        self.layer_invert_mask_check = QCheckBox(qt_t("image_enhancer.layer_invert_mask", "Invert mask"))
        self.layer_workflow_combo = QComboBox()
        for key, label, _filename in WORKFLOW_CHOICES:
            self.layer_workflow_combo.addItem(label, key)

        self.layer_strength_label = QLabel("0.65")
        self.layer_strength_label.setObjectName("muted")
        self.layer_strength_slider = QSlider(Qt.Horizontal)
        self.layer_strength_slider.setRange(0, 100)

        self.layer_opacity_label = QLabel("1.00")
        self.layer_opacity_label.setObjectName("muted")
        self.layer_opacity_slider = QSlider(Qt.Horizontal)
        self.layer_opacity_slider.setRange(0, 100)

        detail_layout.addWidget(QLabel(qt_t("image_enhancer.layer_name", "Layer name")))
        detail_layout.addWidget(self.layer_name_edit)

        detail_layout.addWidget(QLabel(qt_t("image_enhancer.layer_workflow", "Workflow")))
        detail_layout.addWidget(self.layer_workflow_combo)

        detail_layout.addWidget(self.layer_enabled_check)
        detail_layout.addWidget(self.layer_use_mask_check)
        detail_layout.addWidget(self.layer_invert_mask_check)

        strength_row = QHBoxLayout()
        strength_row.addWidget(QLabel(qt_t("image_enhancer.layer_strength", "Strength")))
        strength_row.addStretch(1)
        strength_row.addWidget(self.layer_strength_label)
        detail_layout.addLayout(strength_row)
        detail_layout.addWidget(self.layer_strength_slider)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel(qt_t("image_enhancer.layer_opacity", "Opacity")))
        opacity_row.addStretch(1)
        opacity_row.addWidget(self.layer_opacity_label)
        detail_layout.addLayout(opacity_row)
        detail_layout.addWidget(self.layer_opacity_slider)

        self.right_layout.addWidget(self.layer_detail_card)

        self.export_panel = ExportFoldoutPanel(qt_t("image_enhancer.export_run", "Export And Run"))
        self.export_panel.set_values("", self.service.state.output_options.file_prefix, self.service.state.output_options.open_folder_after_run, self.service.state.output_options.export_session_json)
        self.export_panel.set_expanded(False)
        self.export_panel.export_btn.hide()
        self.right_layout.addWidget(self.export_panel)

        self.right_layout.addStretch(1)
        return card

    def _bind_actions(self) -> None:
        self.load_btn.clicked.connect(self._pick_inputs)
        self.save_mask_btn.clicked.connect(self._save_current_mask)
        self.clear_mask_btn.clicked.connect(self._clear_mask)
        self.undo_btn.clicked.connect(self.canvas.undo)
        self.redo_btn.clicked.connect(self.canvas.redo)
        self.fit_btn.clicked.connect(self.canvas.fit_view)
        self.open_workflows_btn.clicked.connect(lambda: self.service.reveal_workflows_dir())

        self.input_list.currentRowChanged.connect(self._on_input_selected)
        self.canvas.mask_changed.connect(self._on_canvas_mask_changed)

        self.layer_list.currentRowChanged.connect(self._on_layer_selected)
        self.add_layer_btn.clicked.connect(self._add_layer)
        self.duplicate_layer_btn.clicked.connect(self._duplicate_layer)
        self.remove_layer_btn.clicked.connect(self._remove_layer)
        self.layer_up_btn.clicked.connect(lambda: self._move_layer(-1))
        self.layer_down_btn.clicked.connect(lambda: self._move_layer(1))

        self.layer_name_edit.textEdited.connect(lambda text: self._update_selected_layer("name", text))
        self.layer_enabled_check.toggled.connect(lambda value: self._update_selected_layer("enabled", value))
        self.layer_use_mask_check.toggled.connect(lambda value: self._update_selected_layer("use_mask", value))
        self.layer_invert_mask_check.toggled.connect(lambda value: self._update_selected_layer("invert_mask", value))
        self.layer_workflow_combo.currentIndexChanged.connect(self._on_layer_workflow_changed)
        self.layer_strength_slider.valueChanged.connect(self._on_strength_changed)
        self.layer_opacity_slider.valueChanged.connect(self._on_opacity_changed)

        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.export_panel.run_requested.connect(self._run)
        self.export_panel.toggle_requested.connect(self._toggle_export_details)
        self.log_signal.connect(self._on_log)
        self.finished_signal.connect(self._on_finished)

    def _refresh_all(self) -> None:
        self._refresh_inputs()
        self._refresh_layers()
        self._refresh_selected_input()
        self._refresh_selected_layer()
        self._refresh_runtime_status()

    def _refresh_inputs(self) -> None:
        self.input_list.blockSignals(True)
        self.input_list.clear()
        for index, asset in enumerate(self.service.state.input_assets):
            label = asset.path.name
            if asset.mask_path and asset.mask_path.exists():
                label = f"{label}  [mask]"
            item = QListWidgetItem(label)
            item.setToolTip(str(asset.path))
            self.input_list.addItem(item)
            if index == self.service.state.selected_input_index:
                self.input_list.setCurrentRow(index)
        self.input_list.blockSignals(False)
        self.asset_count_badge.setText(qt_t("image_enhancer.asset_count", "{count} images", count=len(self.service.state.input_assets)))

    def _refresh_selected_input(self) -> None:
        current = self.service.current_input()
        if current is None:
            self.selected_input_label.setText(qt_t("image_enhancer.active_input_none", "No input selected"))
            self.mask_status_label.setText(qt_t("image_enhancer.mask_status_none", "Mask: none"))
            self.canvas_status.setText(qt_t("image_enhancer.canvas_empty", "Load an image to start painting."))
            return
        self.selected_input_label.setText(current.path.name)
        self.mask_status_label.setText(
            qt_t(
                "image_enhancer.mask_status_value",
                "Mask: {state}",
                state="saved" if current.mask_path and current.mask_path.exists() else "unpainted",
            )
        )
        if self.canvas.load_image(current.path):
            if current.mask_path and current.mask_path.exists():
                self.canvas.load_mask(current.mask_path)
                self.canvas_status.setText(qt_t("image_enhancer.canvas_mask", "Loaded mask for {name}.", name=current.path.name))
            else:
                self.canvas.clear_mask()
                self.canvas_status.setText(qt_t("image_enhancer.canvas_loaded", "Loaded {name}.", name=current.path.name))

    def _refresh_layers(self) -> None:
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for index, layer in enumerate(self.service.state.layers):
            workflow_label = self.service.workflow_label(layer.workflow_key)
            prefix = "✓" if layer.enabled else "×"
            item = QListWidgetItem(f"{prefix} {layer.name}  [{workflow_label}]")
            item.setToolTip(layer.name)
            self.layer_list.addItem(item)
            if index == self.service.state.selected_layer_index:
                self.layer_list.setCurrentRow(index)
        self.layer_list.blockSignals(False)
        enabled_count = sum(1 for layer in self.service.state.layers if layer.enabled)
        self.layers_summary.setText(
            qt_t("image_enhancer.layers_summary", "{enabled} enabled layer(s), {total} total", enabled=enabled_count, total=len(self.service.state.layers))
        )

    def _refresh_selected_layer(self) -> None:
        layer = self.service.selected_layer()
        if layer is None:
            return
        self.layer_name_edit.blockSignals(True)
        self.layer_enabled_check.blockSignals(True)
        self.layer_use_mask_check.blockSignals(True)
        self.layer_invert_mask_check.blockSignals(True)
        self.layer_workflow_combo.blockSignals(True)
        self.layer_strength_slider.blockSignals(True)
        self.layer_opacity_slider.blockSignals(True)

        self.layer_name_edit.setText(layer.name)
        self.layer_enabled_check.setChecked(layer.enabled)
        self.layer_use_mask_check.setChecked(layer.use_mask)
        self.layer_invert_mask_check.setChecked(layer.invert_mask)
        workflow_index = self.layer_workflow_combo.findData(layer.workflow_key)
        if workflow_index >= 0:
            self.layer_workflow_combo.setCurrentIndex(workflow_index)
        self.layer_strength_slider.setValue(int(layer.strength * 100))
        self.layer_strength_label.setText(f"{layer.strength:.2f}")
        self.layer_opacity_slider.setValue(int(layer.opacity * 100))
        self.layer_opacity_label.setText(f"{layer.opacity:.2f}")

        self.layer_name_edit.blockSignals(False)
        self.layer_enabled_check.blockSignals(False)
        self.layer_use_mask_check.blockSignals(False)
        self.layer_invert_mask_check.blockSignals(False)
        self.layer_workflow_combo.blockSignals(False)
        self.layer_strength_slider.blockSignals(False)
        self.layer_opacity_slider.blockSignals(False)

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

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            APP_TITLE,
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;All Files (*)",
        )
        if files:
            self.service.add_inputs(files)
            self._refresh_all()

    def _save_current_mask(self) -> None:
        index = self.service.state.selected_input_index
        current = self.service.current_input()
        if current is None or index < 0:
            QMessageBox.information(self, APP_TITLE, qt_t("image_enhancer.no_input", "Load an image first."))
            return
        mask_path = self.service.mask_path_for_input(index)
        if mask_path is None:
            return
        if self.canvas.save_mask(mask_path):
            self.service.set_input_mask(index, mask_path)
            self._refresh_inputs()
            self.canvas_status.setText(qt_t("image_enhancer.mask_saved", "Saved mask for {name}.", name=current.path.name))

    def _clear_mask(self) -> None:
        self.canvas.clear_mask()
        self._save_current_mask()

    def _on_canvas_mask_changed(self) -> None:
        self.canvas_status.setText(qt_t("image_enhancer.mask_dirty", "Mask edited. Save it before switching input."))
        self.mask_status_label.setText(qt_t("image_enhancer.mask_status_dirty", "Mask: edited"))

    def _on_input_selected(self, row: int) -> None:
        if row < 0:
            return
        self._save_current_mask()
        self.service.select_input(row)
        self._refresh_selected_input()

    def _add_layer(self) -> None:
        self.service.add_layer()
        self._refresh_layers()
        self._refresh_selected_layer()

    def _duplicate_layer(self) -> None:
        self.service.duplicate_layer(self.service.state.selected_layer_index)
        self._refresh_layers()
        self._refresh_selected_layer()

    def _remove_layer(self) -> None:
        self.service.remove_layer(self.service.state.selected_layer_index)
        self._refresh_layers()
        self._refresh_selected_layer()

    def _move_layer(self, delta: int) -> None:
        self.service.move_layer(self.service.state.selected_layer_index, delta)
        self._refresh_layers()
        self._refresh_selected_layer()

    def _on_layer_selected(self, row: int) -> None:
        if row < 0:
            return
        self.service.state.selected_layer_index = row
        self._refresh_selected_layer()

    def _update_selected_layer(self, key: str, value: object) -> None:
        self.service.update_layer(self.service.state.selected_layer_index, key, value)
        self._refresh_layers()

    def _on_layer_workflow_changed(self, _index: int) -> None:
        key = self.layer_workflow_combo.currentData()
        if key:
            self._update_selected_layer("workflow_key", key)
            self._refresh_layers()

    def _on_strength_changed(self, value: int) -> None:
        strength = value / 100.0
        self.layer_strength_label.setText(f"{strength:.2f}")
        self._update_selected_layer("strength", strength)

    def _on_opacity_changed(self, value: int) -> None:
        opacity = value / 100.0
        self.layer_opacity_label.setText(f"{opacity:.2f}")
        self._update_selected_layer("opacity", opacity)

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

    def _reveal_output_dir(self) -> None:
        self._collect_output_options()
        self.service.reveal_output_dir()

    def _run(self) -> None:
        if self.is_running:
            return
        if not self.service.state.input_assets:
            QMessageBox.information(self, APP_TITLE, qt_t("image_enhancer.no_inputs", "Add at least one image first."))
            return
        ok, message = self.service.workflow_status()
        if not ok:
            QMessageBox.warning(self, APP_TITLE, message)
            return

        self._save_current_mask()
        self._collect_output_options()
        self.is_running = True
        self.runtime_status_badge.setText(qt_t("image_enhancer.running", "Running..."))
        self.export_panel.run_btn.setEnabled(False)

        def worker() -> None:
            try:
                self.service.run(log=lambda msg: self.log_signal.emit(msg))
                self.finished_signal.emit(True, "")
            except Exception as exc:  # noqa: BLE001
                self.finished_signal.emit(False, str(exc))

        import threading

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

    def _refresh_all(self) -> None:
        self._refresh_inputs()
        self._refresh_layers()
        self._refresh_selected_input()
        self._refresh_selected_layer()
        self._refresh_runtime_status()

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if paths:
                self.service.add_inputs(paths)
                self._refresh_all()
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        if self._settings.value("is_maximized", False, bool):
            self.showMaximized()

    def closeEvent(self, event) -> None:
        self._save_current_mask()
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app_root = Path(__file__).resolve().parents[3] / "image_enhancer"
    window = ImageEnhancerWindow(ImageEnhancerService(), app_root, targets)
    window.show()
    return app.exec()
