from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Optional

from contexthub.ui.qt.shell import (
    HeaderSurface,
    apply_app_icon,
    build_shell_stylesheet,
    build_size_grip,
    get_shell_metrics,
    runtime_settings_signature,
)

# Shared Components & Utilities
from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.icon_utils import get_icon

# Refactored Modules
from ai_text_lab_constants import (
    APP_ID, APP_TITLE, DEFAULT_MODEL, 
    SYSTEM_PROMPT_BASE, NO_THINK_INSTRUCTION, DIRECT_OUTPUT_PROMPT
)
from ai_text_lab_worker import StreamWorker
from ai_text_lab_ui_components import OpacityPopup, EditorPanel, PillActionsBar
from ai_text_lab_service import AITextLabService
from ai_text_lab_state import AITextLabState

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, QEvent, QPoint
    from PySide6.QtGui import QClipboard, QTextCursor
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QFrame, QHBoxLayout, 
        QLabel, QMainWindow, QVBoxLayout, QWidget, 
        QProgressBar, QSplitter, QToolButton
    )
except ImportError as exc:
    raise ImportError("PySide6 is required.") from exc

class AITextLabWindow(QMainWindow):
    def __init__(self, state: AITextLabState, app_root: str | Path) -> None:
        super().__init__()
        self.state = state
        self.service = AITextLabService()
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        
        # Internal State
        self._last_clipboard_text = ""
        self._is_monitoring = False
        self._warmup_thread = None
        
        if "ai_text_lab" not in self.app_root.name:
             self.app_root = self.app_root / "ai_text_lab"

        self._load_config()
        self._setup_window()
        self._build_ui()
        self._bind_actions()
        self._restore_app_state()
        
        # Warm-up model in background
        self._init_backend()

    def _setup_window(self):
        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        apply_app_icon(self, self.app_root / "icon.png")
        self.setStyleSheet(build_shell_stylesheet())

    def _init_backend(self):
        """Warm up the default model without blocking UI."""
        def warmup():
            try:
                self.service.warmup_model(DEFAULT_MODEL)
                self.status_label.setText(f"Ready ({DEFAULT_MODEL})")
            except Exception as e:
                self.status_label.setText(f"Backend Error: {e}")
        
        self.status_label.setText(f"Warming up {DEFAULT_MODEL}...")
        self._warmup_thread = threading.Thread(target=warmup, daemon=True)
        self._warmup_thread.start()

    def _load_config(self):
        config_path = self.app_root / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if "presets" in config:
                        self.state.presets.update(config["presets"])
            except: pass

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(14, 14, 14, 14)
        shell_layout.setSpacing(10)

        # 1. Header & Controls
        self.header = HeaderSurface(self, APP_TITLE, "", self.app_root)
        self.header.open_webui_btn.hide()
        self.header.set_header_visibility(show_subtitle=False, show_asset_count=False, show_runtime_status=False)
        self._setup_header_buttons()
        shell_layout.addWidget(self.header)

        # 2. Action Bar
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.state.presets.keys())
        self.preset_combo.setFixedHeight(34)
        
        self.history_btn = build_icon_button("", icon_name="refresh-cw", role="ghost")
        self.history_btn.setFixedSize(34, 34)
        self.run_btn = build_icon_button("RUN", icon_name="play", role="primary")
        self.run_btn.setFixedSize(74, 34)
        
        action_row.addWidget(self.preset_combo, 1)
        action_row.addWidget(self.history_btn)
        action_row.addWidget(self.run_btn)
        shell_layout.addLayout(action_row)

        # 3. Content Splitter
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(2)

        # Input
        self.input_panel = EditorPanel("Input", placeholder="Paste text here...")
        self.input_edit = self.input_panel.editor
        self.input_edit.installEventFilter(self)
        self.splitter.addWidget(self.input_panel)

        # Output
        self.output_container = QWidget()
        out_layout = QVBoxLayout(self.output_container)
        out_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress = QProgressBar()
        self.progress.setFixedHeight(2)
        self.progress.setTextVisible(False)
        self.progress.hide()
        
        self.output_panel = EditorPanel("Output", is_readonly=True, placeholder="Result...")
        self.output_edit = self.output_panel.editor
        
        self.pill_bar = PillActionsBar()
        self.auto_run_btn = self.pill_bar.auto_run_btn
        self.refine_btn = self.pill_bar.refine_btn
        self.copy_btn = self.pill_bar.copy_btn
        
        out_layout.addWidget(self.progress)
        out_layout.addWidget(self.output_panel, 1)
        out_layout.addLayout(self.pill_bar)
        
        self.splitter.addWidget(self.output_container)
        shell_layout.addWidget(self.splitter, 1)

        # 4. Status Bar
        footer = QHBoxLayout()
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-size: 10px; color: rgba(255, 255, 255, 0.4);")
        footer.addStretch()
        footer.addWidget(self.status_label)
        shell_layout.addLayout(footer)

        shell_layout.addWidget(build_size_grip(), 0, Qt.AlignRight)
        root.addWidget(self.window_shell)

    def _setup_header_buttons(self):
        if hasattr(self.header, "maximize_btn"):
            self.header.maximize_btn.hide()

        # Pin Button
        self.pin_btn = QToolButton()
        self.pin_btn.setObjectName("windowChrome")
        self.pin_btn.setIcon(get_icon("pin", color="white"))
        self.pin_btn.setToolTip("Always on Top")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setFixedSize(28, 28)

        # Opacity Button
        self.opacity_btn = QToolButton()
        self.opacity_btn.setObjectName("windowChrome")
        self.opacity_btn.setIcon(get_icon("droplets", color="white"))
        self.opacity_btn.setToolTip("Transparency")
        self.opacity_btn.setFixedSize(28, 28)
        
        self.opacity_popup = OpacityPopup(self, int(self.windowOpacity() * 100))
        self.opacity_popup.valueChanged.connect(lambda v: self.setWindowOpacity(v/100.0))

        h_row = self.header.chrome_row
        c_idx = h_row.indexOf(self.header.close_btn)
        h_row.insertWidget(c_idx, self.pin_btn)
        h_row.insertWidget(c_idx, self.opacity_btn)

    def _bind_actions(self) -> None:
        self.run_btn.clicked.connect(self._on_run)
        self.copy_btn.clicked.connect(self._on_copy)
        self.refine_btn.clicked.connect(self._on_use_as_input)
        self.history_btn.clicked.connect(self._show_history)
        self.pin_btn.toggled.connect(self._on_pin_toggled)
        self.opacity_btn.clicked.connect(lambda: self.opacity_popup.show_above(self.opacity_btn))
        self.auto_run_btn.toggled.connect(lambda: self.status_label.setText("👁️ Clipboard Monitoring Active" if self.auto_run_btn.isChecked() else "Ready"))
        QApplication.clipboard().dataChanged.connect(self._on_clipboard_changed)

    def _on_run(self):
        text = self.input_edit.toPlainText().strip()
        if not text: return
        
        self.output_edit.clear()
        self.progress.show()
        self.progress.setRange(0, 0)
        self.status_label.setText("⚡ Thinking...")
        self.run_btn.setEnabled(False)
        
        preset = self.preset_combo.currentText()
        prompt_template = self.state.presets.get(preset, "Refine:")
        
        # 'nothink' logic injection
        instruction = ""
        if "summarize" not in preset.lower():
            instruction = NO_THINK_INSTRUCTION

        sys_prompt = f"{SYSTEM_PROMPT_BASE}{instruction}{DIRECT_OUTPUT_PROMPT}"
        full_prompt = f"{prompt_template}\n\nText:\n{text}"
        
        self.worker = StreamWorker(self.service, DEFAULT_MODEL, sys_prompt, full_prompt)
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker.chunk_received.connect(lambda c: self.output_edit.insertPlainText(c))
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.thread.start()

    def _on_finished(self, msg):
        self.progress.hide()
        self.status_label.setText("✅ Done")
        self.run_btn.setEnabled(True)
        # Add to history
        self.state.add_history(self.input_edit.toPlainText(), self.output_edit.toPlainText(), self.preset_combo.currentText())

    def _on_error(self, err):
        self.progress.hide()
        self.status_label.setText(f"❌ Error: {err}")
        self.run_btn.setEnabled(True)

    def _on_copy(self):
        QApplication.clipboard().setText(self.output_edit.toPlainText())
        self.status_label.setText("📋 Copied to Clipboard")

    def _on_pin_toggled(self, checked):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self.show()

    def _on_clipboard_changed(self):
        if not self.auto_run_btn.isChecked(): return
        text = QApplication.clipboard().text().strip()
        if text and text != self._last_clipboard_text:
            self._last_clipboard_text = text
            self.input_edit.setPlainText(text)
            self._on_run()

    def _on_use_as_input(self):
        self.input_edit.setPlainText(self.output_edit.toPlainText())
        self.output_edit.clear()

    def _show_history(self):
        if not self.state.history: 
            self.status_label.setText("Empty History")
            return
        # Simple cycling for mini app
        self._history_idx = getattr(self, "_history_idx", 0) % len(self.state.history)
        item = self.state.history[self._history_idx]
        self.input_edit.setPlainText(item["input"])
        self.output_edit.setPlainText(item["output"])
        self.status_label.setText(f"📜 History {self._history_idx + 1}")
        self._history_idx += 1

    def eventFilter(self, obj, event):
        if obj is self.input_edit and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
                self._on_run()
                return True
        return super().eventFilter(obj, event)

    def _restore_app_state(self):
        geo = self._settings.value("geometry")
        if geo: self.restoreGeometry(geo)
        op = self._settings.value("opacity", 100, type=int)
        self.setWindowOpacity(op/100.0)
        self.opacity_popup.slider.setValue(op)

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "opacity_popup") and self.opacity_popup.isVisible():
            self.opacity_popup.show_above(self.opacity_btn)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("opacity", int(self.windowOpacity() * 100))
        try: self.service.unload_model(DEFAULT_MODEL)
        except: pass
        super().closeEvent(event)

def start_app():
    app = QApplication.instance() or QApplication(sys.argv)
    state = AITextLabState()
    # Find app root correctly
    app_root = Path(__file__).resolve().parents[3] / "ai_text_lab"
    window = AITextLabWindow(state, app_root)
    window.show()
    return app.exec()

if __name__ == "__main__":
    import json
    sys.exit(start_app())
