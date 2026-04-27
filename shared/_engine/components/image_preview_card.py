from __future__ import annotations

from shared._engine.components.preview_card_base import build_preview_card_base


def build_image_preview_card(title: str = "Image Preview") -> dict[str, object]:
    return build_preview_card_base(
        title,
        "Image preview",
        "Resolution / channels / format",
    )
