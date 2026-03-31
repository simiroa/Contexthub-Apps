from __future__ import annotations

from .theme_metrics import ShellMetrics
from .theme_palette import ShellPalette


def build_control_styles(p: ShellPalette, m: ShellMetrics) -> str:
    return f"""
        QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
            background: {p.field_bg};
            color: {p.text};
            border: 1px solid {p.control_border};
            border-radius: {m.field_radius}px;
            padding: {m.input_padding_y}px {m.input_padding_x}px;
            selection-background-color: rgba(75, 141, 255, 0.35);
        }}
        QComboBox:hover, QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
            border-color: rgba(255,255,255,0.18);
        }}
        QComboBox::drop-down {{
            width: 28px;
            border: none;
            background: transparent;
        }}
    """
