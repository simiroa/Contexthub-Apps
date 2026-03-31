from __future__ import annotations

from .theme_palette import ShellPalette
from .theme_tone import ToneSpec


def build_text_styles(
    p: ShellPalette,
    accent: ToneSpec,
    success: ToneSpec,
    warning: ToneSpec,
    error: ToneSpec,
    muted: ToneSpec,
) -> str:
    return f"""
        QLabel#sectionTitle {{
            font-size: 16px;
            font-weight: 700;
        }}
        QLabel#title {{
            color: {p.text};
            font-size: 14px;
            font-weight: 700;
        }}
        QLabel#summaryText, QLabel#muted, QLabel#mutedSmall {{
            color: {p.text_muted};
        }}
        QLabel#mutedSmall {{
            font-size: 11px;
        }}
        QLabel#statusKey {{
            color: {p.text_muted};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.08em;
        }}
        QLabel#statusValue {{
            color: {p.text};
            font-size: 18px;
            font-weight: 700;
        }}
        QLabel#statusValueRunning {{
            color: {p.success};
            font-size: 18px;
            font-weight: 700;
        }}
        QLabel#statusValueStopped {{
            color: {p.error};
            font-size: 18px;
            font-weight: 700;
        }}
        QLabel#eyebrow {{
            color: {p.text_muted};
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        QLabel#chip {{
            color: {p.chip_text};
            background: {p.chip_bg};
            border: 1px solid {p.chip_border};
            border-radius: 12px;
            padding: 6px 10px;
            font-size: 11px;
            font-weight: 700;
        }}
        QLabel[badgeRole="chip"],
        QLabel[badgeRole="status"] {{
            border-radius: 12px;
            padding: 6px 10px;
            font-size: 11px;
            font-weight: 700;
        }}
        QLabel[badgeRole="chip"][tone="accent"],
        QLabel[badgeRole="status"][tone="accent"] {{
            color: {accent.text};
            background: {accent.fill};
            border: 1px solid {accent.border};
        }}
        QLabel[badgeRole="chip"][tone="success"],
        QLabel[badgeRole="status"][tone="success"] {{
            color: {success.text};
            background: {success.fill};
            border: 1px solid {success.border};
        }}
        QLabel[badgeRole="chip"][tone="warning"],
        QLabel[badgeRole="status"][tone="warning"] {{
            color: {warning.text};
            background: {warning.fill};
            border: 1px solid {warning.border};
        }}
        QLabel[badgeRole="chip"][tone="error"],
        QLabel[badgeRole="status"][tone="error"] {{
            color: {error.text};
            background: {error.fill};
            border: 1px solid {error.border};
        }}
        QLabel[badgeRole="chip"][tone="muted"],
        QLabel[badgeRole="status"][tone="muted"] {{
            color: {muted.text};
            background: {muted.fill};
            border: 1px solid {muted.border};
        }}
        QLabel[badgeRole="chip"][tone="default"],
        QLabel[badgeRole="status"][tone="default"] {{
            color: {p.chip_text};
            background: {p.chip_bg};
            border: 1px solid {p.chip_border};
        }}
        QLabel#windowTitle {{
            color: {p.text};
            font-size: 18px;
            font-weight: 800;
        }}
        QLabel#windowSubTitle {{
            color: {p.text_muted};
            font-size: 12px;
        }}
    """
