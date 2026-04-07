from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role


def build_empty_state_card(title: str = "No Items Yet", body: str = "Add input to begin.") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    set_surface_role(card, "subtle")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(6)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    body_label = QLabel(body)
    body_label.setObjectName("summaryText")
    body_label.setWordWrap(True)
    body_label.setAlignment(Qt.AlignCenter)

    layout.addWidget(title_label)
    layout.addWidget(body_label)
    return {"card": card, "title_label": title_label, "body_label": body_label}
