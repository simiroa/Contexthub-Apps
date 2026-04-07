from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from contexthub.ui.qt.shell import set_button_role
from shared._engine.components.icon_button import build_icon_button


def build_toolbar_row(title: str = "View", action_text: str = "Refresh", icon_name: str | None = None) -> dict[str, object]:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    label = QLabel(title)
    combo = QComboBox()
    action = build_icon_button(action_text, icon_name=icon_name, role="secondary")
    layout.addWidget(label)
    layout.addWidget(combo, 0)
    layout.addStretch(1)
    layout.addWidget(action, 0)
    return {"widget": host, "label": label, "combo": combo, "action": action}
