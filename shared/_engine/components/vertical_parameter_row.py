from __future__ import annotations

from PySide6.QtWidgets import QWidget

from shared._engine.components.field_row import LabeledFieldRow

class VerticalParameterRow(LabeledFieldRow):
    """
    Standardized Vertical Parameter Row for Contexthub-Apps.
    Ensures a consistent Label (Eyebrow) + Field stacking layout with proper 10px bold eyebrow font.
    """
    def __init__(self, label_text: str, field: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(
            label_text,
            field,
            orientation="vertical",
            margins=(0, 4, 0, 8),
            spacing=6,
            parent=parent,
        )
