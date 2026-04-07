from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from contexthub.ui.qt.shell import get_shell_metrics, set_button_role, set_surface_role


def build_queue_card(title: str = "Queue", *, compact: bool = True) -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    header = QHBoxLayout()
    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    count_label = QLabel("0")
    count_label.setObjectName("summaryText")
    clear_btn = QPushButton("Clear")
    set_button_role(clear_btn, "secondary")
    header.addWidget(title_label)
    header.addStretch(1)
    header.addWidget(count_label)
    header.addWidget(clear_btn)
    layout.addLayout(header)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    if compact:
        scroll.setMinimumHeight(84)
        scroll.setMaximumHeight(120)
    body = QWidget()
    set_surface_role(scroll.viewport(), "subtle")
    set_surface_role(body, "subtle")
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(10, 10, 10, 10)
    body_layout.setSpacing(8)
    body_layout.addStretch(1)
    scroll.setWidget(body)
    layout.addWidget(scroll)

    return {
        "card": card,
        "count_label": count_label,
        "clear_btn": clear_btn,
        "scroll": scroll,
        "body": body,
        "body_layout": body_layout,
    }
