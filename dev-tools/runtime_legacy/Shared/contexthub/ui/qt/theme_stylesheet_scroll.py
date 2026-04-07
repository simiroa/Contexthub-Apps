from __future__ import annotations


def build_scroll_styles(combo_arrow: str | None = None) -> str:
    return f"""
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        QScrollArea > QWidget > QScrollBar {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 8px 0 8px 0;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255,255,255,0.14);
            border-radius: 4px;
            min-height: 28px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: rgba(255,255,255,0.24);
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: transparent;
            height: 0px;
        }}
    """
