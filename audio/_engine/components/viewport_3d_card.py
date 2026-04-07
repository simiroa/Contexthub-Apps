from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_button_role, set_surface_role


def build_viewport_3d_card(title: str = "3D Viewport") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    viewport = QFrame()
    set_surface_role(viewport, "subtle")
    viewport.setMinimumHeight(200)
    viewport_layout = QVBoxLayout(viewport)
    viewport_layout.setContentsMargins(10, 10, 10, 10)
    viewport_label = QLabel("3D preview surface")
    viewport_label.setAlignment(Qt.AlignCenter)
    viewport_layout.addWidget(viewport_label, 1)
    layout.addWidget(viewport)

    toolbar = QHBoxLayout()
    camera_btn = QPushButton("Reset View")
    wire_btn = QPushButton("Wireframe")
    set_button_role(camera_btn, "secondary")
    set_button_role(wire_btn, "secondary")
    toolbar.addWidget(camera_btn)
    toolbar.addWidget(wire_btn)
    toolbar.addStretch(1)
    layout.addLayout(toolbar)

    status = QLabel("Triangles / materials / bounds")
    status.setObjectName("summaryText")
    layout.addWidget(status)

    return {
        "card": card,
        "viewport": viewport,
        "camera_btn": camera_btn,
        "wire_btn": wire_btn,
        "status": status,
    }
