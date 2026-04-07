from __future__ import annotations

from PySide6.QtWidgets import QFrame, QListWidget, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics


def build_history_panel(title: str = "History") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    list_widget = QListWidget()
    layout.addWidget(title_label)
    layout.addWidget(list_widget, 1)
    return {"card": card, "list_widget": list_widget}
