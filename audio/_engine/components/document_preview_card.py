from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role


def build_document_preview_card(title: str = "Document Preview") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    page_surface = QFrame()
    set_surface_role(page_surface, "subtle")
    page_surface.setMinimumHeight(180)
    page_layout = QVBoxLayout(page_surface)
    page_layout.setContentsMargins(10, 10, 10, 10)
    page_label = QLabel("Page preview / thumbnail")
    page_label.setAlignment(Qt.AlignCenter)
    page_layout.addWidget(page_label, 1)
    layout.addWidget(page_surface)

    meta = QLabel("Pages / OCR / scan status")
    meta.setObjectName("summaryText")
    layout.addWidget(meta)

    return {"card": card, "page_surface": page_surface, "page_label": page_label, "meta": meta}
