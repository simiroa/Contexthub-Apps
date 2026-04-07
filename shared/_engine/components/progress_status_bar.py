from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget

from contexthub.ui.qt.shell import set_button_role
from shared._engine.components.icon_button import build_icon_button


def build_progress_status_bar(action_text: str = "Run", icon_name: str | None = None) -> dict[str, object]:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    status = QLabel("Ready")
    status.setObjectName("summaryText")
    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(0)
    action = build_icon_button(action_text, icon_name=icon_name, role="primary")

    layout.addWidget(status, 0)
    layout.addWidget(progress, 1)
    layout.addWidget(action, 0)
    return {"widget": host, "status": status, "progress": progress, "action": action}
