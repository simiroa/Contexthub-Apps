from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role


def build_preview_card(title: str, placeholder: str = "No Preview") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QHBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(12)

    preview_box = QFrame()
    set_surface_role(preview_box, "subtle")
    preview_box.setMinimumSize(180, 120)
    preview_layout = QVBoxLayout(preview_box)
    preview_layout.setContentsMargins(10, 10, 10, 10)
    preview_label = QLabel(placeholder)
    preview_label.setAlignment(Qt.AlignCenter)
    preview_layout.addWidget(preview_label, 1)
    layout.addWidget(preview_box, 0)

    info_col = QVBoxLayout()
    info_col.setSpacing(6)
    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    meta_label = QLabel("")
    meta_label.setObjectName("summaryText")
    meta_label.setWordWrap(True)
    info_col.addWidget(title_label)
    info_col.addWidget(meta_label)
    info_col.addStretch(1)
    layout.addLayout(info_col, 1)

    return {
        "card": card,
        "preview_box": preview_box,
        "preview_label": preview_label,
        "title_label": title_label,
        "meta_label": meta_label,
    }
