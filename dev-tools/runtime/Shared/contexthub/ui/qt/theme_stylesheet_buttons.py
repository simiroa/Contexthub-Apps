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
            background: rgba(184, 115, 121, 0.22);
            border-color: rgba(184, 115, 121, 0.45);
        }}
        QPushButton#primary {{
            background: {p.accent};
            color: {p.accent_text};
            border: 1px solid {p.accent};
            border-radius: 12px;
            padding: 8px 14px;
            font-weight: 700;
        }}
        QPushButton#primary:hover {{
            background: {p.accent_hover};
            border-color: {p.accent_hover};
        }}
        QPushButton#pillBtn {{
            background: {p.button_bg};
            color: {p.text};
            border: 1px solid {p.control_border};
            border-radius: 999px;
            padding: 8px 14px;
        }}
        QPushButton#pillBtn:hover {{
            background: {p.button_hover};
        }}
        QPushButton#ghostBtn {{
            background: transparent;
            color: {p.text_muted};
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 7px 12px;
        }}
        QPushButton#ghostBtn:hover {{
            background: {p.button_hover};
            color: {p.text};
        }}
        QPushButton#secondaryBtn {{
            background: {p.button_bg};
            color: {p.text};
            border: 1px solid {p.control_border};
            border-radius: 12px;
            padding: 8px 14px;
        }}
        QPushButton#secondaryBtn:hover {{
            background: {p.button_hover};
        }}
        QPushButton:disabled {{
            color: {p.text_muted};
            background: rgba(255,255,255,0.03);
            border-color: rgba(255,255,255,0.05);
        }}
    """
