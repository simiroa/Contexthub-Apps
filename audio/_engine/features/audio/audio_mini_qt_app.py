from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from contexthub.ui.qt.shell import (
    HeaderSurface,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    set_badge_role,
)
from features.audio.audio_toolbox_service import AudioToolboxService
from features.audio.audio_toolbox_state import AudioToolboxState
from features.audio.audio_toolbox_tasks import (
    TASK_LABELS,
    TASK_STACK_INDEX,
    export_formats_for_task,
    TASK_COMPRESS_AUDIO,
)

# Shared components
from components.mini_execute_card import build_mini_execute_card
from components.mini_parameter_card import build_mini_parameter_slider

class ServiceBridge(QObject):
    updated = Signal(dict)

    def emit_update(self, **payload) -> None:
        self.updated.emit(payload)


class AudioMiniWindow(QMainWindow):
    def __init__(
        self,
        targets: list[Path],
        app_root: Path,
        default_task: str,
        title: str,
        subtitle: str = "",
    ):
        super().__init__()
        self.targets = targets
        self.app_root = app_root
        self.default_task = default_task
        self.app_title = title
        
        # Unique app_id to allow multiple instances
        self.app_id = f"audio_mini_{default_task}"
        
        self.state = AudioToolboxState()
        self.state.current_task = default_task
        self.app_subtitle = subtitle
        self.bridge = ServiceBridge()
        self.bridge.updated.connect(self._on_service_update)
        self.service = AudioToolboxService(self.state, on_update=self.bridge.emit_update)

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self._init_ui()
        self._sync_from_state()

    def _init_ui(self) -> None:
        self.setWindowTitle(self.app_title)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._sync_from_state()

        # Dynamic size fitting
        self.setFixedWidth(420)
        if self.centralWidget() and self.centralWidget().layout():
            self.centralWidget().layout().setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        self.adjustSize()

        # Center the window
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)

        shell = QFrame()
        shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header = HeaderSurface(self, self.app_title, self.app_subtitle, self.app_root)
        self.header.set_header_visibility(show_subtitle=False, show_asset_count=True, show_runtime_status=True)
        shell_layout.addWidget(self.header)

        # Execution Card (Simplified Mini)
        self.export_card = build_mini_execute_card("Process")
        self.export_format_combo = self.export_card["format_combo"]
        self.export_format_combo.currentTextChanged.connect(self._on_export_format_changed)

        # Optional Profile/Quality Slider (Integrated into the same card)
        if self.default_task == TASK_COMPRESS_AUDIO:
            self.quality_card = build_mini_parameter_slider(
                "Quality", 
                value_labels={0: "High", 1: "Balanced", 2: "Small"}
            )
            # Add the contents of the parameter card elements to the options_layout
            self.export_card["options_layout"].addWidget(self.quality_card["card"])
            # Remove the frame/background of the nested card to make it look integrated
            self.quality_card["card"].setStyleSheet("background: transparent; border: none; padding: 0;")
            
            self.quality_slider = self.quality_card["slider"]
            self.quality_slider.valueChanged.connect(self._on_compress_level_changed)

        self.export_card["run_btn"].clicked.connect(self._run_task)
        self.export_card["cancel_btn"].clicked.connect(self.service.cancel)
        self.export_card["reveal_btn"].clicked.connect(self.service.reveal_output_dir)
        shell_layout.addWidget(self.export_card["card"])

        root.addWidget(shell)

    def _sync_from_state(self) -> None:
        self.header.set_asset_count(len(self.targets))
        
        # Setup format choices
        formats = export_formats_for_task(self.default_task)
        self.export_format_combo.clear()
        self.export_format_combo.addItems(formats)
        
        if self.state.export_format in formats:
            self.export_format_combo.setCurrentText(self.state.export_format)
            
    def _on_export_format_changed(self, fmt: str) -> None:
        self.state.export_format = fmt

    def _on_compress_level_changed(self, idx: int) -> None:
        # In Compress Audio, levels are Quality(0), Balanced(1), Small(2)
        # This matches our slider labels
        levels = ["Quality", "Balanced", "Small"]
        if 0 <= idx < len(levels):
            self.state.compress_level = levels[idx]

    def _on_service_update(self, payload: dict) -> None:
        status = payload.get("status", "")
        progress = payload.get("progress", 0)
        
        self.export_card["status_label"].setText(status)
        if progress > 0:
            self.export_card["progress_label"].setText(f"{progress}%")
        else:
             self.export_card["progress_label"].setText("")

        if payload.get("finished"):
            self.header.set_runtime_status("idle")
        elif payload.get("error"):
             QMessageBox.critical(self, "Error", payload["error"])

    def _run_task(self) -> None:
        if not self.targets:
            QMessageBox.warning(self, "No Files", "Please provide input files via command line.")
            return
        self.header.set_runtime_status("processing")
        self.service.start_batch(self.targets)


def start_mini_app(targets: list[Path]|None, app_root: str|Path, app_id: str, title: str, description: str = "") -> int:
    state = AudioToolboxState(files=[Path(item) for item in (targets or [])])
    if state.files:
        state.selected_index = 0
    
    # Check for existing instance before creating a new one
    existing_instance = QApplication.instance()
    app = existing_instance or QApplication(sys.argv)
    
    window = AudioMiniWindow(state.files, Path(app_root), app_id, title, description)
    window.show()
    
    # Only execute the event loop if we created the app instance here
    if not existing_instance:
        return app.exec()
    return 0
