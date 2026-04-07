from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics


def build_status_card(title: str, body_text: str) -> tuple[QFrame, QLabel]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    status_label = QLabel(body_text)
    status_label.setObjectName("summaryText")
    status_label.setWordWrap(True)
    layout.addWidget(status_label)
    return card, status_label
