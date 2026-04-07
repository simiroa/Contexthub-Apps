from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from contexthub.ui.qt.shell import get_shell_metrics
from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.icon_utils import get_icon


def build_collapsible_section(title: str, *, expanded: bool = False) -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    header = QHBoxLayout()
    header.setSpacing(8)
    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    
    toggle_btn = build_icon_button("", icon_name="chevron-up" if expanded else "chevron-down", role="secondary", is_icon_only=True)
    toggle_btn.setCheckable(True)
    toggle_btn.setChecked(expanded)
    
    header.addWidget(title_label)
    header.addStretch(1)
    header.addWidget(toggle_btn)
    layout.addLayout(header)

    summary_label = QLabel("Collapsed section")
    summary_label.setObjectName("summaryText")
    layout.addWidget(summary_label)

    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(10)
    layout.addWidget(content)

    def _sync() -> None:
        is_open = toggle_btn.isChecked()
        toggle_btn.setIcon(get_icon("chevron-up" if is_open else "chevron-down", color="#94a3b8"))
        content.setVisible(is_open)
        summary_label.setVisible(not is_open)

    toggle_btn.clicked.connect(_sync)
    _sync()

    return {
        "card": card,
        "toggle_btn": toggle_btn,
        "title_label": title_label,
        "summary_label": summary_label,
        "content": content,
        "content_layout": content_layout,
    }
