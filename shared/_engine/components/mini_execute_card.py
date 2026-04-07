from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from contexthub.ui.qt.shell import get_shell_metrics, get_shell_palette
from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.icon_utils import get_icon


class MiniExecuteCard(QFrame):
    """
    Standardized, ultra-compact execution card for 'mini' template apps.
    Features a clean 26px action footer and standard status tracking.
    """
    
    run_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, title: str = "Process", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.m = get_shell_metrics()
        self.p = get_shell_palette()
        self.setObjectName("none") # Remove card background/border
        self.setFrameShape(QFrame.NoFrame)
        self._init_ui(title)

    def _init_ui(self, title: str):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, self.m.panel_padding, 0, 0)
        self.layout.setSpacing(0)

        # Status Bar components kept internally for API compatibility but hidden
        self.status_label = QLabel("Ready")
        self.status_label.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)

        # 4. Action Row (Consolidated: Format | Save)
        self.action_layout = QHBoxLayout()
        self.action_layout.setSpacing(8)
        self.action_layout.setContentsMargins(0, 0, 0, 0)

        # Format Selector - Standardize to 32px height
        self.format_combo = QComboBox()
        self.format_combo.setObjectName("compactField")
        self.format_combo.addItems(["Original", "PNG", "JPG"])
        self.format_combo.setFixedHeight(32)
        
        self.cancel_btn = build_icon_button("", icon_name="x", role="ghost")
        self.cancel_btn.setFixedSize(32, 32)
        self.cancel_btn.setVisible(False)
        
        self.run_btn = build_icon_button(title, icon_name="play", role="primary")
        self.run_btn.setFixedHeight(32)

        self.action_layout.addWidget(self.format_combo, 1) # Balanced 1:1
        self.action_layout.addWidget(self.cancel_btn)
        self.action_layout.addWidget(self.run_btn, 1)    # Balanced 1:1
        
        self.layout.addLayout(self.action_layout)

        # Connections
        self.run_btn.clicked.connect(self.run_clicked.emit)
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)

    def set_status(self, status: str, progress: Optional[str] = None):
        self.status_label.setText(status)
        if progress is not None:
            self.progress_label.setText(progress)

    def set_running(self, running: bool):
        self.run_btn.setEnabled(not running)
        self.format_combo.setEnabled(not running)
        self.cancel_btn.setVisible(running)
        self.run_btn.setIcon(get_icon("loader" if running else "play", color="white"))
        if not running:
            self.set_status("Ready", "")


def build_mini_execute_card(title: str = "Process") -> dict[str, object]:
    card_obj = MiniExecuteCard(title)
    return {
        "card": card_obj,
        "options_layout": card_obj.options_layout,
        "format_combo": card_obj.format_combo,
        "cancel_btn": card_obj.cancel_btn,
        "run_btn": card_obj.run_btn,
        "status_label": card_obj.status_label,
        "progress_label": card_obj.progress_label,
    }
