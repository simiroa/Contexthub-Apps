from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QWidget

from contexthub.ui.qt.shell import get_shell_metrics
from shared._engine.components.field_row import LabeledFieldRow


class ParameterRow(LabeledFieldRow):
    """
    Standardized Parameter Row for Contexthub-Apps.
    Ensures a consistent Label (Eyebrow) + Field layout with proper spacing and 26px alignment.
    """
    
    def __init__(self, label_text: str, field: QWidget, parent: Optional[QWidget] = None):
        super().__init__(
            label_text,
            field,
            orientation="horizontal",
            label_width=60,
            margins=(0, 0, 0, 0),
            spacing=8,
            fixed_height=get_shell_metrics().input_min_height,
            parent=parent,
        )
