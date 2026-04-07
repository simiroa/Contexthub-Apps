from __future__ import annotations

from .theme_metrics import ShellMetrics
from .theme_palette import ShellPalette


def build_button_styles(p: ShellPalette, m: ShellMetrics) -> str:
    return f"""
        QToolButton#windowChrome,
        QPushButton#titleBtn,
        QPushButton#titleBtnClose {{
            background: {p.chrome_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.title_btn_radius}px;
            min-width: {m.title_btn_size}px;
            min-height: {m.title_btn_size}px;
            color: {p.text};
            font-weight: 700;
        }}
        QToolButton#windowChrome:hover,
        QPushButton#titleBtn:hover {{
            background: {p.chrome_hover};
        }}
        QPushButton#titleBtnClose:hover {{
            background: {p.error_soft};
            border-color: {p.error};
        }}
        QPushButton#primary, QPushButton[buttonRole="primary"] {{
            background: {p.accent};
            color: {p.accent_text};
            border: 1px solid {p.accent};
            border-radius: {m.field_radius}px;
            padding: 4px 12px;
            font-weight: 700;
            min-height: {m.primary_button_height}px;
            text-transform: none;
        }}
        QPushButton#primary:hover, QPushButton[buttonRole="primary"]:hover {{
            background: {p.accent_hover};
            border-color: {p.accent_hover};
        }}
        QPushButton#pillBtn, QPushButton[buttonRole="pill"] {{
            background: {p.button_bg};
            color: {p.text};
            border: 1px solid {p.control_border};
            border-radius: 999px;
            padding: 8px 14px;
            min-height: {m.input_min_height}px;
        }}
        QPushButton#pillBtn:hover, QPushButton[buttonRole="pill"]:hover {{
            background: {p.button_hover};
        }}
        QPushButton#ghostBtn, QPushButton[buttonRole="ghost"] {{
            background: transparent;
            color: {p.text_muted};
            border: 1px solid transparent;
            border-radius: {m.field_radius}px;
            padding: 4px 10px;
            min-height: {m.input_min_height}px;
        }}
        QPushButton#ghostBtn:hover, QPushButton[buttonRole="ghost"]:hover {{
            background: {p.button_hover};
            color: {p.text};
        }}
        QPushButton#secondaryBtn, QPushButton[buttonRole="secondary"] {{
            background: {p.button_bg};
            color: {p.text};
            border: 1px solid {p.control_border};
            border-radius: {m.field_radius}px;
            padding: 4px 12px;
            min-height: {m.input_min_height}px;
        }}
        QPushButton#secondaryBtn:hover, QPushButton[buttonRole="secondary"]:hover {{
            background: {p.button_hover};
        }}
        QPushButton:disabled {{
            color: {p.text_muted};
            background: {p.surface_subtle_ghost};
            border-color: {p.control_border};
            opacity: 0.6;
        }}
        QPushButton#iconBtn, QPushButton[buttonRole="icon"] {{
            min-height: {m.input_min_height}px;
            max-height: {m.input_min_height}px;
            min-width: {m.input_min_height}px;
            max-width: {m.input_min_height}px;
            padding: 0px;
            border-radius: {m.field_radius}px;
            background: transparent;
            color: {p.text};
            border: 1px solid {p.control_border};
        }}
        QPushButton#iconBtn:hover, QPushButton[buttonRole="icon"]:hover {{
            background: {p.button_hover};
            border-color: rgba(255, 255, 255, 0.15);
        }}
        QPushButton#iconBtn:pressed, QPushButton[buttonRole="icon"]:pressed {{
            background: {p.surface_subtle_ghost};
        }}
        QPushButton#segmentBtn, QPushButton[buttonRole="segment"] {{
            min-height: {m.input_min_height}px;
            padding: 4px 10px;
            border-radius: {m.field_radius}px;
            background: {p.control_bg};
            border: 1px solid {p.control_border};
            color: {p.text};
        }}
        QPushButton#segmentBtn:hover, QPushButton[buttonRole="segment"]:hover {{
            background: {p.button_hover};
        }}
        QPushButton#segmentBtn:checked, QPushButton[buttonRole="segment"]:checked {{
            background: {p.accent_soft};
            border: 1px solid {p.accent};
            color: {p.accent};
            font-weight: 700;
        }}
    """
