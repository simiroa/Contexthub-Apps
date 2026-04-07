from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role


def build_image_preview_card(title: str = "Image Preview") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    preview = QFrame()
    set_surface_role(preview, "subtle")
    preview.setMinimumHeight(160)
    preview_layout = QVBoxLayout(preview)
    preview_layout.setContentsMargins(10, 10, 10, 10)
    preview_label = QLabel("Image preview")
    preview_label.setAlignment(Qt.AlignCenter)
    preview_layout.addWidget(preview_label, 1)
    layout.addWidget(preview)

    meta = QLabel("Resolution / channels / format")
    meta.setObjectName("summaryText")
    layout.addWidget(meta)

    return {"card": card, "preview": preview, "preview_label": preview_label, "meta": meta}
