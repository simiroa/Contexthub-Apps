from __future__ import annotations

from shared._engine.components.preview_card_base import build_preview_card_base


def build_document_preview_card(title: str = "Document Preview") -> dict[str, object]:
    return build_preview_card_base(
        title,
        "Page preview / thumbnail",
        "Pages / OCR / scan status",
        surface_key="page_surface",
        label_key="page_label",
        min_height=180,
    )
