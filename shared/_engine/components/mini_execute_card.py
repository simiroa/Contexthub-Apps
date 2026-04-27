from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from contexthub.ui.qt.shell import get_shell_metrics
from shared._engine.components.execution_footer import ExecutionFooter


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
        self.setObjectName("none") # Remove card background/border
        self.setFrameShape(QFrame.NoFrame)
        self._init_ui(title)

    def _init_ui(self, title: str):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, self.m.panel_padding, 0, 0)
        self.layout.setSpacing(0)

        self.footer = ExecutionFooter(title, include_format=True, include_cancel=True, cancel_text="")
        self.action_layout = self.footer.layout
        self.options_layout = self.action_layout
        self.format_combo = self.footer.format_combo
        self.cancel_btn = self.footer.cancel_btn
        self.run_btn = self.footer.run_btn
        self.status_label = self.footer.status_label
        self.progress_label = self.footer.progress_label
        self.layout.addWidget(self.footer)

        # Connections
        self.run_btn.clicked.connect(self.run_clicked.emit)
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)

    def set_status(self, status: str, progress: Optional[str] = None):
        self.footer.set_status(status, progress)

    def set_running(self, running: bool):
        self.footer.set_running(running)


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
