from __future__ import annotations

import sys
from pathlib import Path
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
    apply_rounded_window_mask,
    build_shell_stylesheet,
    get_shell_metrics,
)
from features.audio.audio_toolbox_service import AudioToolboxService
from features.audio.audio_toolbox_state import AudioToolboxState
from features.audio.audio_toolbox_tasks import (
    TASK_CONVERT_AUDIO,
    export_formats_for_task,
    TASK_COMPRESS_AUDIO,
    TASK_ENHANCE_AUDIO,
)

# Shared components
from shared._engine.components.export_foldout_card import build_export_foldout_card
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
        
        self.state = AudioToolboxState(files=list(targets))
        self.state.task_type = default_task
        if self.state.files:
            self.state.selected_index = 0
        self.app_subtitle = subtitle
        self.bridge = ServiceBridge()
        self.bridge.updated.connect(self._on_service_update)
        self.service = AudioToolboxService(self.state, on_update=self.bridge.emit_update)

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self._init_ui()
        self._sync_from_state()

    def _init_ui(self) -> None:
        self.setWindowTitle(self.app_title)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
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
        apply_rounded_window_mask(self, get_shell_metrics().window_radius)

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        shell = QFrame()
        shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header = HeaderSurface(self, self.app_title, self.app_subtitle, self.app_root)
        self.header.set_header_visibility(show_subtitle=False, show_asset_count=True, show_runtime_status=True)
        shell_layout.addWidget(self.header)

        # Execution Card (Standardized Export Foldout)
        self.export_card = build_export_foldout_card("Process")
        self.export_format_combo = self.export_card["out_format_combo"]
        self.export_format_combo.currentTextChanged.connect(self._on_export_format_changed)

        self.export_card["name_edit"].setText("processed")
        self.export_card["name_edit"].setPlaceholderText("output_filename")

        # Optional Profile/Quality Slider (Integrated into the same card)
        if self.default_task == TASK_COMPRESS_AUDIO:
            self.quality_card = build_mini_parameter_slider(
                "Quality", 
                value_labels={0: "High", 1: "Balanced", 2: "Small"},
                embedded=True,
            )
            self.export_card["details_layout"].insertWidget(0, self.quality_card["card"])
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

        current_format = ""
        if self.default_task == TASK_COMPRESS_AUDIO:
            current_format = self.state.compress_output_format
        elif self.default_task == TASK_CONVERT_AUDIO:
            current_format = self.state.convert_output_format
        elif self.default_task == TASK_ENHANCE_AUDIO:
            current_format = self.state.enhance_output_format

        if current_format in formats:
            self.export_format_combo.setCurrentText(current_format)
            
    def _on_export_format_changed(self, fmt: str) -> None:
        if self.default_task == TASK_COMPRESS_AUDIO:
            self.state.compress_output_format = fmt.upper()
        elif self.default_task == TASK_CONVERT_AUDIO:
            self.state.convert_output_format = fmt.upper()
        elif self.default_task == TASK_ENHANCE_AUDIO:
            self.state.enhance_output_format = fmt.upper()

    def _on_compress_level_changed(self, idx: int) -> None:
        # In Compress Audio, levels are Quality(0), Balanced(1), Small(2)
        # This matches our slider labels
        levels = ["Quality", "Balanced", "Small"]
        if 0 <= idx < len(levels):
            self.state.compress_level = levels[idx]

    def _on_service_update(self, payload: dict) -> None:
        progress = int(round((self.state.progress_value or 0.0) * 100))
        self.export_card["progress_percent"].setText(f"{progress}%")
        self.export_card["card"].set_running(self.state.is_processing)
        self.export_card["card"].set_progress(progress, self.state.status_text or None)

        if payload.get("finished"):
            self.header.set_runtime_status("idle")
        elif payload.get("error"):
             QMessageBox.critical(self, "Error", payload["error"])

    def _run_task(self) -> None:
        if not self.targets:
            QMessageBox.warning(self, "No Files", "Please provide input files via command line.")
            return
        self.header.set_runtime_status("processing")
        self.state.files = list(self.targets)
        if self.state.selected_index < 0 and self.state.files:
            self.state.selected_index = 0
        self.service.start()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        apply_rounded_window_mask(self, get_shell_metrics().window_radius)


def start_mini_app(targets: list[Path]|None, app_root: str|Path, app_id: str, title: str, description: str = "") -> int:
    state = AudioToolboxState(files=[Path(item) for item in (targets or [])])
    if state.files:
        state.selected_index = 0
    
    # Check for existing instance before creating a new one
    existing_instance = QApplication.instance()
    app = existing_instance or QApplication(sys.argv)
    
    window = AudioMiniWindow(
        targets=state.files,
        app_root=Path(app_root),
        default_task=app_id,
        title=title,
        subtitle=description
    )
    window.show()
    
    # Only execute the event loop if we created the app instance here
    if not existing_instance:
        return app.exec()
    return 0
