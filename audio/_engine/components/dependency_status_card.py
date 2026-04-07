from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_badge_role


def build_dependency_status_card(title: str = "Dependencies") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    status_badge = QLabel("Ready")
    set_badge_role(status_badge, "status", "success")
    meta = QLabel("ffmpeg / blender / model runtime state")
    meta.setObjectName("summaryText")
    layout.addWidget(title_label)
    layout.addWidget(status_badge)
    layout.addWidget(meta)
    return {"card": card, "status_badge": status_badge, "meta": meta}
