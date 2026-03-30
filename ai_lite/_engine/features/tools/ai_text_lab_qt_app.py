from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import List, Optional

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
from ai_text_lab_service import AITextLabService
from ai_text_lab_state import AITextLabState

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, Signal, QObject, QEvent, QPoint, QSize
    from PySide6.QtGui import QIcon, QAction, QColor, QClipboard
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
        QProgressBar,
        QSlider,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for AI Text Lab.") from exc

APP_ID = "ai_text_lab"
APP_TITLE = qt_t("ai_text_lab.title", "AI Text Lab Pro")

class StreamWorker(QObject):
    chunk_received = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, service: AITextLabService, model: str, system_prompt: str, prompt: str):
        super().__init__()
        self.service = service
        self.model = model
        self.system_prompt = system_prompt
        self.prompt = prompt
        self.cancel_event = threading.Event()

    def run(self):
        try:
            if self.model.startswith("✦ "):
                self.service.stream_gemini(self.model, self.system_prompt, self.prompt, self.chunk_received.emit, self.cancel_event)
            else:
                self.service.stream_ollama(self.model, self.system_prompt, self.prompt, 0, self.chunk_received.emit, self.cancel_event)
            self.finished.emit("Completed")
        except Exception as e:
            self.error.emit(str(e))

class AITextLabWindow(QMainWindow):
    PRESETS = {
        "🔍 Grammar Fix": "Correct the grammar of the following text. Fix grammatical errors, typos, and punctuation. Maintain the original tone and style. Output ONLY the corrected text.",
        "📝 Summarize": "Summarize the following text into concise bullet points. Extract key information, be brief. Output ONLY the summary.",
        "📋 3줄 요약 (한글)": "Summarize the following text into exactly 3 concise bullet points in Korean. Output ONLY the summary.",
        "📧 Pro Email": "Rewrite the following text as a professional email. Formal, polite, concise, structured for business. Output ONLY the rewritten text.",
        "🎨 Midjourney Prompt": "Rewrite the following text as a high-quality Midjourney prompt. Enhance visual descriptions, add lighting/style keywords (e.g., cinematic lighting, 8k, hyperrealistic), remove conversational filler. Comma separated. Output ONLY the prompt.",
        "🇰🇷 To Korean": "Translate the following text to natural, fluent Korean. Native-level phrasing. Output ONLY the translation.",
        "🇺🇸 To English": "Translate the following text to natural, fluent English. Native-level phrasing. Output ONLY the translation.",
    }

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
        
        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(380, 580)
        self.setMinimumSize(300, 450)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(self._get_custom_stylesheet())
        self._build_ui()
        self._restore_app_state()
        self._bind_actions()
        
        QTimer.singleShot(100, self._init_backend)

    def _get_custom_stylesheet(self) -> str:
        base = build_shell_stylesheet()
        custom = """
        #windowShell {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(32, 38, 54, 0.98), stop:1 rgba(18, 22, 32, 1.0));
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 16px;
        }
        #glassCard {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-top: 1px solid rgba(255, 255, 255, 0.15); /* Inner Glow */
            border-radius: 12px;
        }
        QLabel#title {
            font-size: 14px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.2px;
        }
        QComboBox {
            padding: 0 10px;
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            color: #e0e6ed;
            font-size: 12px;
        }
        QComboBox::drop-down { border: none; width: 24px; }
        QTextEdit#inputArea, QTextEdit#outputArea {
            background: transparent; border: none; font-size: 13px; color: #e0e6ed; padding: 4px;
            selection-background-color: rgba(74, 144, 226, 0.4);
        }
        QPushButton#primaryAction {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4A90E2, stop:1 #357ABD);
            color: white; border-radius: 8px; font-weight: 800; font-size: 12px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        QPushButton#primaryAction:hover { background: #5CA1F3; outline: none; }
        
        /* Unified Ghost Button Style */
        QPushButton#ghostBtn {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 6px;
            color: #d4dbe5;
            font-size: 14px;
        }
        QPushButton#ghostBtn:hover {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        QPushButton#ghostBtn:checked {
            background: rgba(74, 144, 226, 0.15);
            border: 1px solid rgba(74, 144, 226, 0.4);
            color: #4A90E2;
        }

        /* Action Pill Style */
        QPushButton#pillBtn {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: #e0e6ed;
            font-size: 11px;
            font-weight: 600;
            padding: 4px 10px;
        }
        QPushButton#pillBtn:hover {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        QPushButton#pillBtn:checked {
            background: #4A90E2;
            border-color: #5CA1F3;
            color: white;
        }
        """
        return base + custom

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

        # --- Unified Header ---
        self.header = HeaderSurface(self, APP_TITLE, "", self.app_root)
        self.header.open_webui_btn.hide()
        self.header.set_header_visibility(
            show_subtitle=False,
            show_asset_count=False,
            show_runtime_status=False,
        )
        
        # Apply Ghost Style to Header Buttons
        header_btns = [self.header.min_btn, self.header.max_btn, self.header.close_btn]
        for btn in header_btns:
            btn.setObjectName("ghostBtn")
            btn.setFixedSize(28, 28)

        # Opacity System (Reveal on click)
        self.opacity_wrap = QWidget()
        op_wrap_layout = QHBoxLayout(self.opacity_wrap)
        op_wrap_layout.setContentsMargins(0, 0, 0, 0)
        op_wrap_layout.setSpacing(4)
        
        self.opacity_btn = QPushButton("🌓")
        self.opacity_btn.setObjectName("ghostBtn")
        self.opacity_btn.setCheckable(True)
        self.opacity_btn.setFixedSize(28, 28)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setFixedWidth(50)
        self.opacity_slider.setVisible(False)
        
        op_wrap_layout.addWidget(self.opacity_btn)
        op_wrap_layout.addWidget(self.opacity_slider)
        
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setObjectName("ghostBtn")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setFixedSize(28, 28)

        h_row = self.header.chrome_row
        if h_row:
            # Title spatial fix
            h_row.setContentsMargins(0, 0, 0, 0)
            c_idx = h_row.indexOf(self.header.close_btn)
            h_row.insertWidget(c_idx - 2, self.opacity_wrap)
            h_row.insertWidget(c_idx - 2, self.pin_btn)
        
        shell_layout.addWidget(self.header)

        # --- Preset & Run ---
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.PRESETS.keys())
        self.preset_combo.setFixedHeight(34)
        
        self.run_btn = QPushButton("RUN")
        self.run_btn.setObjectName("primaryAction")
        self.run_btn.setFixedSize(70, 34)
        
        preset_row.addWidget(self.preset_combo, 1)
        preset_row.addWidget(self.run_btn)
        shell_layout.addLayout(preset_row)

        # --- Input Card ---
        input_card = QFrame()
        input_card.setObjectName("glassCard")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        self.input_edit = QTextEdit()
        self.input_edit.setObjectName("inputArea")
        self.input_edit.setPlaceholderText("Paste text to process...")
        self.input_edit.setFixedHeight(110)
        self.input_edit.setAcceptRichText(False)
        input_layout.addWidget(self.input_edit)
        shell_layout.addWidget(input_card)

        # --- Result Card with Floating Pills ---
        self.result_card = QFrame()
        self.result_card.setObjectName("glassCard")
        res_root = QVBoxLayout(self.result_card)
        res_root.setContentsMargins(0, 0, 0, 0)
        res_root.setSpacing(0)
        
        # Overlay container for text + floating pills
        overlay_container = QWidget()
        container_layout = QVBoxLayout(overlay_container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        
        self.progress = QProgressBar()
        self.progress.setFixedHeight(2)
        self.progress.setTextVisible(False)
        self.progress.hide()
        
        self.output_edit = QTextEdit()
        self.output_edit.setObjectName("outputArea")
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Optimized results will stream here...")
        
        container_layout.addWidget(self.progress)
        container_layout.addWidget(self.output_edit)
        
        # Action Pills Layer (Inside result card but separate from text flow if possible)
        pill_row = QHBoxLayout()
        pill_row.setContentsMargins(8, 0, 8, 8)
        pill_row.setSpacing(6)
        
        self.auto_run_btn = QPushButton("📡 Auto-Run")
        self.auto_run_btn.setCheckable(True)
        self.auto_run_btn.setObjectName("pillBtn")
        self.auto_run_btn.setFixedHeight(24)
        
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setObjectName("pillBtn")
        self.copy_btn.setFixedHeight(24)
        
        pill_row.addWidget(self.auto_run_btn)
        pill_row.addStretch()
        pill_row.addWidget(self.copy_btn)
        
        res_root.addWidget(overlay_container, 1)
        res_root.addLayout(pill_row)
        
        shell_layout.addWidget(self.result_card, 1)

        # --- Model Footer ---
        footer_info = QHBoxLayout()
        footer_info.setContentsMargins(4, 0, 4, 0)
        
        self.model_combo = QComboBox()
        self.model_combo.setFixedHeight(22)
        self.model_combo.setFixedWidth(140)
        self.model_combo.setStyleSheet("font-size: 10px; background: rgba(0,0,0,0.3); padding: 0 4px;")
        
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("muted")
        self.status_label.setStyleSheet("font-size: 10px;")
        
        footer_info.addWidget(self.model_combo)
        footer_info.addStretch()
        footer_info.addWidget(self.status_label)
        shell_layout.addLayout(footer_info)

        # Grip for resizing
        grip_row = QHBoxLayout()
        grip_row.addStretch()
        self.size_grip = build_size_grip()
        grip_row.addWidget(self.size_grip)
        shell_layout.addLayout(grip_row)

        root.addWidget(self.window_shell)

    def _bind_actions(self) -> None:
        self.run_btn.clicked.connect(self._on_run)
        self.copy_btn.clicked.connect(self._on_copy)
        self.pin_btn.toggled.connect(self._on_pin_toggled)
        self.opacity_btn.toggled.connect(self._on_opacity_reveal_toggled)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.auto_run_btn.toggled.connect(self._on_auto_run_toggled)
        
        self.input_edit.installEventFilter(self)
        QApplication.clipboard().dataChanged.connect(self._on_clipboard_changed)

    def eventFilter(self, obj, event):
        if obj is self.input_edit and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and event.modifiers() & Qt.ControlModifier:
                self._on_run()
                return True
        return super().eventFilter(obj, event)

    def _init_backend(self):
        models = self.service.list_ollama_models()
        self.model_combo.clear()
        self.model_combo.addItems(["✦ gemini-2.0-flash", "✦ gemini-1.5-flash"] + models)
        
        saved_model = self._settings.value("last_model")
        if saved_model:
            idx = self.model_combo.findText(saved_model)
            if idx >= 0: self.model_combo.setCurrentIndex(idx)
        self.status_label.setText("Ready")

    def _on_run(self):
        text = self.input_edit.toPlainText().strip()
        if not text: return
        
        self.output_edit.clear()
        self.progress.show()
        self.progress.setRange(0, 0)
        self.status_label.setText("⚡ Processing...")
        self.run_btn.setEnabled(False)
        
        preset = self.preset_combo.currentText()
        prompt_template = self.PRESETS.get(preset, "Refine:")
        model = self.model_combo.currentText()
        
        system_prompt = "You are a professional editor. Output only the refined text without any explanation."
        full_prompt = f"{prompt_template}\n\nText:\n{text}"
        
        self.worker = StreamWorker(self.service, model, system_prompt, full_prompt)
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        
        self.worker.chunk_received.connect(self._on_chunk)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.thread.start()

    def _on_chunk(self, chunk):
        self.output_edit.moveCursor(self.output_edit.textCursor().End)
        self.output_edit.insertPlainText(chunk)

    def _on_finished(self, msg):
        self.progress.hide()
        self.status_label.setText("✨ Done")
        self.run_btn.setEnabled(True)
        self._settings.setValue("last_model", self.model_combo.currentText())
        self._settings.setValue("last_preset", self.preset_combo.currentText())

    def _on_error(self, err):
        self.progress.hide()
        self.status_label.setText("⚠️ Failed")
        self.run_btn.setEnabled(True)

    def _on_copy(self):
        content = self.output_edit.toPlainText().strip()
        if content:
            QApplication.clipboard().setText(content)
            self.status_label.setText("✅ Copied")

    def _on_pin_toggled(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def _on_opacity_reveal_toggled(self, checked):
        self.opacity_slider.setVisible(checked)

    def _on_opacity_changed(self, value):
        self.setWindowOpacity(value / 100.0)

    def _on_auto_run_toggled(self, checked):
        self._is_monitoring = checked
        if checked:
            self.status_label.setText("📡 Monitoring")
            self._last_clipboard_text = QApplication.clipboard().text()
        else:
            self.status_label.setText("Ready")

    def _on_clipboard_changed(self):
        if not self._is_monitoring: return
        new_text = QApplication.clipboard().text().strip()
        if new_text and new_text != self._last_clipboard_text:
            self._last_clipboard_text = new_text
            self.input_edit.setPlainText(new_text)
            self._on_run()

    def _restore_app_state(self):
        geo = self._settings.value("geometry")
        if geo: self.restoreGeometry(geo)
        
        preset = self._settings.value("last_preset")
        if preset:
            idx = self.preset_combo.findText(preset)
            if idx >= 0: self.preset_combo.setCurrentIndex(idx)
            
        pinned = self._settings.value("pinned", False, type=bool)
        if pinned:
            self.pin_btn.setChecked(True)
            self._on_pin_toggled(True)
            
        op = self._settings.value("opacity", 100, type=int)
        self.opacity_slider.setValue(op)
        self._on_opacity_changed(op)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("pinned", self.pin_btn.isChecked())
        self._settings.setValue("opacity", self.opacity_slider.value())
        super().closeEvent(event)

def start_app():
    app = QApplication.instance() or QApplication(sys.argv)
    state = AITextLabState()
    window = AITextLabWindow(state, Path(__file__).resolve().parents[3] / "ai_lite" / "ai_text_lab")
    window.show()
    return app.exec()
