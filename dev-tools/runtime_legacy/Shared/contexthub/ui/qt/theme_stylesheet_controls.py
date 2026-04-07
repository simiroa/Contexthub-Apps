from __future__ import annotations

from .theme_metrics import ShellMetrics
from .theme_palette import ShellPalette


from .theme_style_helpers import get_svg_chevron_data_uri


def build_control_styles(p: ShellPalette, m: ShellMetrics) -> str:
    chevron_down = get_svg_chevron_data_uri("down", p.text_muted)
    chevron_up = get_svg_chevron_data_uri("up", p.text_muted)
    
    return f"""
        QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
            background: {p.field_bg};
            color: {p.text};
            border: 1px solid {p.control_border};
            border-radius: {m.field_radius}px;
            min-height: {m.input_min_height}px;
            padding: {m.input_padding_y}px {m.input_padding_x}px;
            selection-background-color: {p.accent_soft};
        }}
        QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {p.accent};
        }}
        QComboBox:hover, QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover {{
            border-color: rgba(255,255,255,0.18);
        }}
        QComboBox {{
            padding-right: 28px;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: center right;
            width: 24px;
            border-left: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: url("{chevron_down}");
            width: 14px;
            height: 14px;
            margin-right: 8px;
        }}
        
        /* SpinBox Modernization */
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid {p.control_border};
            border-bottom: 0px none;
            border-top-right-radius: {m.field_radius}px;
            background: transparent;
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 20px;
            border-left: 1px solid {p.control_border};
            border-top: 0px none;
            border-bottom-right-radius: {m.field_radius}px;
            background: transparent;
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            image: url("{chevron_up}");
            width: 10px; height: 10px;
        }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            image: url("{chevron_down}");
            width: 10px; height: 10px;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background: {p.button_hover};
        }}
    """
