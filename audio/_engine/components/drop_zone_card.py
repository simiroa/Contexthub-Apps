from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role


def build_drop_zone_card(title: str = "Drop Files Here", body: str = "Drag files or folders into this area.") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    set_surface_role(card, "card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    zone = QFrame()
    set_surface_role(zone, "subtle")
    zone.setMinimumHeight(120)
    zone_layout = QVBoxLayout(zone)
    zone_layout.setContentsMargins(10, 10, 10, 10)
    body_label = QLabel(body)
    body_label.setAlignment(Qt.AlignCenter)
    body_label.setWordWrap(True)
    zone_layout.addWidget(body_label, 1)
    layout.addWidget(zone)
    return {"card": card, "zone": zone, "body_label": body_label}
