from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics
from shared._engine.components.icon_button import build_icon_button


def build_input_card(title: str, placeholder: str, action_text: str, icon_name: str | None = None) -> tuple[QFrame, QLineEdit, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    row = QHBoxLayout()
    row.setSpacing(8)
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    button = build_icon_button(action_text, icon_name=icon_name, role="primary")
    row.addWidget(field, 1)
    row.addWidget(button, 0)
    layout.addLayout(row)
    return card, field, button
