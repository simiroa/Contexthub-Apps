from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role


def build_preview_card_base(
    title: str,
    surface_text: str,
    meta_text: str,
    *,
    surface_key: str = "preview",
    label_key: str = "preview_label",
    meta_key: str = "meta",
    min_height: int = 160,
    footer: QWidget | None = None,
    footer_stretch: int = 0,
) -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    surface = QFrame()
    set_surface_role(surface, "subtle")
    surface.setMinimumHeight(min_height)
    surface_layout = QVBoxLayout(surface)
    surface_layout.setContentsMargins(10, 10, 10, 10)

    surface_label = QLabel(surface_text)
    surface_label.setAlignment(Qt.AlignCenter)
    surface_layout.addWidget(surface_label, 1)
    layout.addWidget(surface)

    meta_label = QLabel(meta_text)
    meta_label.setObjectName("summaryText")
    layout.addWidget(meta_label, footer_stretch)

    if footer is not None:
        layout.addWidget(footer)

    return {
        "card": card,
        "title_label": title_label,
        surface_key: surface,
        label_key: surface_label,
        meta_key: meta_label,
    }
