from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSlider,
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
    set_surface_role,
    set_badge_role,
)
from features.audio.audio_toolbox_service import AudioToolboxService
from features.audio.audio_toolbox_state import (
    AudioToolboxState,
    TASK_EXTRACT_ALL_AUDIO,
    TASK_EXTRACT_BGM,
    TASK_EXTRACT_VOICE,
    TASK_LABELS,
)

# Reuse standard components
from shared._engine.components.export_foldout_card import build_export_foldout_card

APP_ID = "extract_audio"
APP_TITLE = "Extract Audio"
APP_SUBTITLE = "Extract audio tracks or isolate vocals/bgm."


class ServiceBridge(QObject):
    updated = Signal(dict)

    def emit_update(self, **payload) -> None:
        self.updated.emit(payload)


class ExtractAudioWindow(QMainWindow):
    def __init__(self, state: AudioToolboxState, app_root: Path) -> None:
        super().__init__()
        self.state = state
        self.app_root = app_root
        self.bridge = ServiceBridge()
        self.bridge.updated.connect(self._on_service_update)
        self.service = AudioToolboxService(self.state, on_update=self.bridge.emit_update)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._sync_from_state()

        # Dynamic size fitting at the end
        self.setFixedWidth(420)
        if self.centralWidget() and self.centralWidget().layout():
            self.centralWidget().layout().setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        self.adjustSize()

        # Center on screen
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
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

        self.header = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        self.header.set_header_visibility(show_subtitle=False, show_asset_count=True, show_runtime_status=True)
        shell_layout.addWidget(self.header)

        # Execution Card (Standardized Export Foldout)
        self.export_card = build_export_foldout_card("Extract")
        self.export_format_combo = self.export_card["out_format_combo"] # Using new dedicated format combo
        
        self.export_format_combo.addItems(["WAV", "MP3", "FLAC", "M4A"])
        self.export_format_combo.setCurrentText(self.state.separator_output_format.upper())
        self.export_format_combo.currentTextChanged.connect(self._on_format_changed)

        # Mode Selection
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_label = QLabel("MODE")
        mode_label.setObjectName("muted")
        mode_label.setFixedWidth(90)
        
        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("compactField")
        self.mode_combo.addItem(TASK_LABELS[TASK_EXTRACT_ALL_AUDIO], TASK_EXTRACT_ALL_AUDIO)
        self.mode_combo.addItem(TASK_LABELS[TASK_EXTRACT_VOICE], TASK_EXTRACT_VOICE)
        self.mode_combo.addItem(TASK_LABELS[TASK_EXTRACT_BGM], TASK_EXTRACT_BGM)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode_combo, 1)
        self.export_card["details_layout"].insertLayout(0, mode_row)

        # Update UI Labels
        self.export_card["name_edit"].setPlaceholderText("extract_audio")
        self.export_card["name_edit"].setText("extract")

        self.export_card["run_btn"].clicked.connect(self._run_task)
        self.export_card["cancel_btn"].clicked.connect(self.service.cancel)
        self.export_card["reveal_btn"].clicked.connect(self.service.reveal_output_dir)
        shell_layout.addWidget(self.export_card["card"])

        root.addWidget(shell)

    def _on_format_changed(self, value: str) -> None:
        self.state.separator_output_format = value.lower()

    def _sync_from_state(self) -> None:
        self.header.set_asset_count(len(self.state.files))
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(self.state.task_type))
        self._refresh_status()

    def _refresh_status(self) -> None:
        self.export_card["progress_percent"].setText(f"{int(self.state.completed_count/self.state.total_count*100)}%" if self.state.total_count else "0%")
        
        tone = "muted"
        if self.state.is_processing:
            tone = "warning"
        elif self.state.error_message:
            tone = "error"
        elif self.state.completed_count and self.state.completed_count == self.state.total_count:
            tone = "success"
            
        set_badge_role(self.header.runtime_status_badge, tone)
        self.header.runtime_status_badge.setText(tone.capitalize())
        self.export_card["run_btn"].setEnabled(not self.state.is_processing and bool(self.state.files))
        self.export_card["cancel_btn"].setEnabled(self.state.is_processing)

    def _on_mode_changed(self, index: int) -> None:
        self.state.task_type = self.mode_combo.itemData(index)

    def _run_task(self) -> None:
        if not self.state.files:
            return
        self.service.start()

    def _on_service_update(self, payload: dict) -> None:
        self._refresh_status()
        if payload.get("finished"):
            errors = payload.get("errors") or []
            if errors:
                QMessageBox.warning(self, APP_TITLE, "\n".join(errors[:3]))
            elif self.state.last_output_path:
                # Optionally notify completion
                pass

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        apply_rounded_window_mask(self, get_shell_metrics().window_radius)


def start_app(targets: list[Path] | None, app_root: Path) -> int:
    state = AudioToolboxState(files=targets or [])
    if targets:
        state.task_type = TASK_EXTRACT_ALL_AUDIO # Default
    
    # Check for existing instance before creating a new one
    existing_instance = QApplication.instance()
    app = existing_instance or QApplication(sys.argv)
    
    window = ExtractAudioWindow(state, app_root)
    window.show()
    
    # Only execute the event loop if we created the app instance here
    if not existing_instance:
        return app.exec()
    return 0
