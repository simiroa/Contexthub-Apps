from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QWidget

from contexthub.ui.qt.shell import set_button_role


def build_progress_status_bar(action_text: str = "Run") -> dict[str, object]:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    status = QLabel("Ready")
    status.setObjectName("summaryText")
    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(0)
    action = QPushButton(action_text)
    set_button_role(action, "primary")

    layout.addWidget(status, 0)
    layout.addWidget(progress, 1)
    layout.addWidget(action, 0)
    return {"widget": host, "status": status, "progress": progress, "action": action}
