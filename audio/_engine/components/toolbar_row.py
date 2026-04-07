from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from contexthub.ui.qt.shell import set_button_role


def build_toolbar_row(title: str = "View", action_text: str = "Refresh") -> dict[str, object]:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    label = QLabel(title)
    combo = QComboBox()
    action = QPushButton(action_text)
    set_button_role(action, "secondary")
    layout.addWidget(label)
    layout.addWidget(combo, 0)
    layout.addStretch(1)
    layout.addWidget(action, 0)
    return {"widget": host, "label": label, "combo": combo, "action": action}
