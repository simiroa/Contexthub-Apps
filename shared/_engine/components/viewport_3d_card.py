from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget

from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.preview_card_base import build_preview_card_base


def build_viewport_3d_card(title: str = "3D Viewport") -> dict[str, object]:
    footer = QWidget()
    toolbar = QHBoxLayout()
    toolbar.setContentsMargins(0, 0, 0, 0)
    camera_btn = build_icon_button("Reset View", icon_name="refresh-cw", role="secondary")
    wire_btn = build_icon_button("Wireframe", icon_name="box", role="secondary")
    toolbar.addWidget(camera_btn)
    toolbar.addWidget(wire_btn)
    toolbar.addStretch(1)
    footer.setLayout(toolbar)

    result = build_preview_card_base(
        title,
        "3D preview surface",
        "Triangles / materials / bounds",
        surface_key="viewport",
        meta_key="status",
        min_height=200,
        footer=footer,
    )
    result["camera_btn"] = camera_btn
    result["wire_btn"] = wire_btn
    return result
