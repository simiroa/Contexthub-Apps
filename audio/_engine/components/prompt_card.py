from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QTextEdit, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics


def build_prompt_card(title: str = "Prompt") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    editor = QTextEdit()
    editor.setPlaceholderText("Enter prompt text")
    layout.addWidget(title_label)
    layout.addWidget(editor, 1)
    return {"card": card, "editor": editor}
