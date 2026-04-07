"""ComfyUI Inpainting Qt App – main window.

Special-template layout:
  Left:  InpaintingCanvas + toolbar
  Right: Parameters card + Export foldout
"""
from __future__ import annotations

import sys
from pathlib import Path

from features.comfyui.inpainting_canvas import InpaintingCanvas
from features.comfyui.inpainting_service import InpaintingService

from contexthub.ui.qt.shell import (
    CollapsibleSection,
    HeaderSurface,
    apply_app_icon,
    attach_size_grip,
    build_shell_stylesheet,
    get_shell_metrics,
    get_shell_palette,
    set_badge_role,
    set_surface_role,
    qt_t,
)

try:
    from PySide6.QtCore import QSettings, QThread, Qt, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QScrollArea,
        QSlider,
        QSpinBox,
        QSplitter,
        QTextEdit,
        QVBoxLayout,
        QWidget,
        QPushButton,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for the Inpainting app.") from exc


APP_ID = "inpainting"
APP_TITLE = qt_t("comfyui.inpainting.title", "ComfyUI Inpainting")
APP_SUBTITLE = qt_t("comfyui.inpainting.subtitle", "Brush mask and regenerate — powered by ComfyUI")


class WorkerThread(QThread):
    finished = Signal(bool, str, object)

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def run(self) -> None:
        ok, msg, payload = self._callback()
        self.finished.emit(ok, msg, payload)


class InpaintingWindow(QMainWindow):
    def __init__(
        self,
        service: InpaintingService,
        app_root: str | Path,
        targets: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._run_thread: WorkerThread | None = None
        self._settings = QSettings("Contexthub", APP_ID)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1400, 920)
        self.setMinimumSize(1100, 720)
        self.setAcceptDrops(True)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._bind_actions()
        self._restore_window_state()

        if targets:
            for t in targets:
                if self.canvas.load_image(t):
                    self.service.set_source_image(t)
                    break

    # ==================================================================
    # UI construction
    # ==================================================================

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

        # Header
        self.header = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root, show_webui=True)
        self.header.set_header_visibility(show_subtitle=True, show_asset_count=False, show_runtime_status=True)
        self.status_badge = self.header.runtime_status_badge
        shell_layout.addWidget(self.header)

        # Splitter: left canvas | right params
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)

        left = self._build_canvas_panel()
        right = self._build_param_panel()
        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 4)
        self.splitter.setSizes([860, 480])
        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    # ------------------------------------------------------------------
    # Left: Canvas + toolbar
    # ------------------------------------------------------------------

    def _build_canvas_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.load_btn = QPushButton("  Load Image")
        self.load_btn.setObjectName("secondary")

        self.brush_label = QLabel("Brush: 30")
        self.brush_label.setObjectName("eyebrow")
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(2, 200)
        self.brush_slider.setValue(30)
        self.brush_slider.setFixedWidth(140)

        self.eraser_btn = QPushButton("Eraser")
        self.eraser_btn.setObjectName("secondary")
        self.eraser_btn.setCheckable(True)

        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setObjectName("ghost")
        self.redo_btn = QPushButton("Redo")
        self.redo_btn.setObjectName("ghost")
        self.clear_btn = QPushButton("Clear Mask")
        self.clear_btn.setObjectName("ghost")
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setObjectName("ghost")

        toolbar.addWidget(self.load_btn)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.brush_label)
        toolbar.addWidget(self.brush_slider)
        toolbar.addSpacing(8)
        toolbar.addWidget(self.eraser_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.undo_btn)
        toolbar.addWidget(self.redo_btn)
        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.fit_btn)

        layout.addLayout(toolbar)

        # Canvas
        self.canvas = InpaintingCanvas()
        layout.addWidget(self.canvas, 1)

        # Drop hint
        self.drop_hint = QLabel(qt_t("comfyui.inpainting.drop_hint", "Drop an image here or click Load Image"))
        self.drop_hint.setObjectName("muted")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.drop_hint)

        return card

    # ------------------------------------------------------------------
    # Right: Params + Export
    # ------------------------------------------------------------------

    def _build_param_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel(qt_t("comfyui.inpainting.parameters", "Parameters"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

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
        layout.addWidget(scroll, 1)

        # Build parameter sections
        self._build_prompt_section()
        self._build_sampling_section()
        self._build_model_section()
        self.param_layout.addStretch(1)

        # Export / Run footer
        footer = QFrame()
        footer.setObjectName("subtlePanel")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 12, 12, 12)
        footer_layout.setSpacing(8)

        self.status_label = QLabel(qt_t("comfyui.inpainting.status_ready", "Ready"))
        self.status_label.setObjectName("summaryText")
        self.status_label.setWordWrap(True)
        footer_layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.reveal_btn = QPushButton("Open Folder")
        self.reveal_btn.setObjectName("ghost")
        self.run_btn = QPushButton(qt_t("comfyui.inpainting.run", "▶  Run Inpainting"))
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumHeight(36)
        btn_row.addWidget(self.reveal_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.run_btn, 1)
        footer_layout.addLayout(btn_row)

        layout.addWidget(footer)
        return card

    def _build_prompt_section(self) -> None:
        section = CollapsibleSection(qt_t("comfyui.inpainting.section_prompt", "Prompt"), expanded=True)

        # Positive prompt
        group1 = QFrame()
        group1.setObjectName("subtlePanel")
        inner1 = QVBoxLayout(group1)
        inner1.setContentsMargins(10, 8, 10, 8)
        inner1.setSpacing(4)
        lbl1 = QLabel("Positive Prompt")
        lbl1.setObjectName("eyebrow")
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Describe what to generate in the masked area...")
        self.prompt_edit.setMaximumHeight(80)
        inner1.addWidget(lbl1)
        inner1.addWidget(self.prompt_edit)
        section.add_widget(group1)

        # Negative prompt
        group2 = QFrame()
        group2.setObjectName("subtlePanel")
        inner2 = QVBoxLayout(group2)
        inner2.setContentsMargins(10, 8, 10, 8)
        inner2.setSpacing(4)
        lbl2 = QLabel("Negative Prompt")
        lbl2.setObjectName("eyebrow")
        self.negative_edit = QTextEdit()
        self.negative_edit.setPlainText(self.service.state.negative_prompt)
        self.negative_edit.setMaximumHeight(60)
        inner2.addWidget(lbl2)
        inner2.addWidget(self.negative_edit)
        section.add_widget(group2)

        section.finish()
        self.param_layout.addWidget(section)

    def _build_sampling_section(self) -> None:
        section = CollapsibleSection(qt_t("comfyui.inpainting.section_sampling", "Sampling"), expanded=True)

        # Steps
        group_steps = self._slider_group("Steps", 1, 50, self.service.state.steps, "steps")
        section.add_widget(group_steps["widget"])
        self._steps_slider = group_steps

        # CFG
        group_cfg = self._slider_group("CFG Scale", 1, 20, int(self.service.state.cfg), "cfg")
        section.add_widget(group_cfg["widget"])
        self._cfg_slider = group_cfg

        # Denoise
        group_denoise = self._slider_group("Denoise Strength", 1, 100, int(self.service.state.denoise * 100), "denoise_pct")
        section.add_widget(group_denoise["widget"])
        self._denoise_slider = group_denoise

        # Sampler combo
        group_sampler = QFrame()
        group_sampler.setObjectName("subtlePanel")
        inner = QVBoxLayout(group_sampler)
        inner.setContentsMargins(10, 8, 10, 8)
        inner.setSpacing(4)
        lbl = QLabel("Sampler")
        lbl.setObjectName("eyebrow")
        self.sampler_combo = QComboBox()
        self.sampler_combo.addItems(["euler", "euler_ancestral", "dpmpp_2m", "dpmpp_sde", "ddim"])
        self.sampler_combo.setCurrentText(self.service.state.sampler)
        inner.addWidget(lbl)
        inner.addWidget(self.sampler_combo)
        section.add_widget(group_sampler)

        # Seed
        group_seed = QFrame()
        group_seed.setObjectName("subtlePanel")
        inner_s = QVBoxLayout(group_seed)
        inner_s.setContentsMargins(10, 8, 10, 8)
        inner_s.setSpacing(4)
        lbl_s = QLabel("Seed (-1 = random)")
        lbl_s.setObjectName("eyebrow")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 2147483647)
        self.seed_spin.setValue(self.service.state.seed)
        inner_s.addWidget(lbl_s)
        inner_s.addWidget(self.seed_spin)
        section.add_widget(group_seed)

        section.finish()
        self.param_layout.addWidget(section)

    def _build_model_section(self) -> None:
        section = CollapsibleSection(qt_t("comfyui.inpainting.section_model", "Model"), expanded=False)

        group = QFrame()
        group.setObjectName("subtlePanel")
        inner = QVBoxLayout(group)
        inner.setContentsMargins(10, 8, 10, 8)
        inner.setSpacing(4)
        lbl = QLabel("Checkpoint")
        lbl.setObjectName("eyebrow")
        self.ckpt_combo = QComboBox()
        self.ckpt_combo.addItem("(not connected)")
        inner.addWidget(lbl)
        inner.addWidget(self.ckpt_combo)
        section.add_widget(group)

        section.finish()
        self.param_layout.addWidget(section)

    def _slider_group(self, label: str, lo: int, hi: int, default: int, key: str) -> dict:
        group = QFrame()
        group.setObjectName("subtlePanel")
        inner = QVBoxLayout(group)
        inner.setContentsMargins(10, 8, 10, 8)
        inner.setSpacing(4)

        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setObjectName("eyebrow")
        val = QLabel(str(default))
        row.addWidget(lbl)
        row.addStretch(1)
        row.addWidget(val)
        inner.addLayout(row)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(default)
        slider.valueChanged.connect(lambda v, k=key, l=val: self._on_slider(k, l, v))
        inner.addWidget(slider)
        return {"widget": group, "slider": slider, "label": val}

    # ==================================================================
    # Actions
    # ==================================================================

    def _bind_actions(self) -> None:
        self.load_btn.clicked.connect(self._pick_image)
        self.brush_slider.valueChanged.connect(self._on_brush_size_changed)
        self.eraser_btn.toggled.connect(self._on_eraser_toggled)
        self.undo_btn.clicked.connect(self.canvas.undo)
        self.redo_btn.clicked.connect(self.canvas.redo)
        self.clear_btn.clicked.connect(self.canvas.clear_mask)
        self.fit_btn.clicked.connect(self.canvas.fit_view)
        self.canvas.image_loaded.connect(self._on_image_loaded)
        self.canvas.mask_changed.connect(self._on_mask_changed)

        self.prompt_edit.textChanged.connect(lambda: self.service.update_parameter("prompt", self.prompt_edit.toPlainText()))
        self.negative_edit.textChanged.connect(lambda: self.service.update_parameter("negative_prompt", self.negative_edit.toPlainText()))
        self.sampler_combo.currentTextChanged.connect(lambda v: self.service.update_parameter("sampler", v))
        self.seed_spin.valueChanged.connect(lambda v: self.service.update_parameter("seed", v))

        self.run_btn.clicked.connect(self._run_inpainting)
        self.reveal_btn.clicked.connect(self.service.reveal_output_dir)

        if hasattr(self.header, "open_webui_btn"):
            self.header.open_webui_btn.clicked.connect(self._open_webui)

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            qt_t("comfyui.inpainting.open_image", "Open Image"),
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;All Files (*)",
        )
        if path:
            if self.canvas.load_image(path):
                self.service.set_source_image(path)

    def _on_image_loaded(self, path: str) -> None:
        self.drop_hint.hide()
        self._update_status(f"Loaded: {Path(path).name}", "ready")

    def _on_mask_changed(self) -> None:
        self.service.set_mask_ready(True)

    def _on_brush_size_changed(self, value: int) -> None:
        self.canvas.brush_size = value
        self.brush_label.setText(f"Brush: {value}")

    def _on_eraser_toggled(self, checked: bool) -> None:
        self.canvas.eraser_mode = checked
        self.eraser_btn.setText("Eraser ✓" if checked else "Eraser")

    def _on_slider(self, key: str, label: QLabel, value: int) -> None:
        if key == "denoise_pct":
            self.service.update_parameter("denoise", value / 100.0)
            label.setText(f"{value}%")
        else:
            self.service.update_parameter(key, value)
            label.setText(str(value))

    def _run_inpainting(self) -> None:
        ok, reason = self.service.can_run()
        if not ok:
            self._update_status(reason, "warning")
            return
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")
        mask = self.canvas.get_mask_pil()
        self._run_thread = WorkerThread(lambda: self.service.run_inpainting(mask))
        self._run_thread.finished.connect(self._on_run_finished)
        self._run_thread.start()

    def _on_run_finished(self, ok: bool, msg: str, payload: object) -> None:
        self.run_btn.setEnabled(True)
        self.run_btn.setText(qt_t("comfyui.inpainting.run", "▶  Run Inpainting"))
        level = "ready" if ok else "warning"
        self._update_status(msg, level)

    def _open_webui(self) -> None:
        import webbrowser
        webbrowser.open("http://127.0.0.1:8188")

    def _update_status(self, text: str, level: str) -> None:
        self.status_label.setText(text)
        tone = {"ready": "success", "warning": "warning", "error": "error"}.get(level, "accent")
        set_badge_role(self.status_badge, "status", tone)
        self.status_badge.setText(text[:40])

    # ==================================================================
    # Drag & drop
    # ==================================================================

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if self.canvas.load_image(path):
                        self.service.set_source_image(path)
                        break
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    # ==================================================================
    # Window state
    # ==================================================================

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app_root = Path(__file__).resolve().parents[3] / APP_ID
    window = InpaintingWindow(InpaintingService(), app_root, targets or [])
    window.show()
    app.exec()
