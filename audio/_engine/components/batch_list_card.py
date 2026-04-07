from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics
from shared._engine.components.icon_button import build_icon_button


def build_batch_list_card(title: str = "Batch Items") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    list_widget = QListWidget()
    layout.addWidget(list_widget, 1)

    actions = QHBoxLayout()
    add_btn = build_icon_button("Add", icon_name="plus", role="secondary")
    remove_btn = build_icon_button("Remove", icon_name="minus", role="secondary")
    clear_btn = build_icon_button("Clear", icon_name="trash-2", role="secondary")
    
    actions.addWidget(add_btn)
    actions.addWidget(remove_btn)
    actions.addWidget(clear_btn)
    actions.addStretch(1)
    layout.addLayout(actions)

    return {
        "card": card,
        "list_widget": list_widget,
        "add_btn": add_btn,
        "remove_btn": remove_btn,
        "clear_btn": clear_btn,
    }
