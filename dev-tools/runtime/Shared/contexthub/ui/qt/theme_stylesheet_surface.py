from __future__ import annotations

from .theme_metrics import ShellMetrics
from .theme_palette import ShellPalette
from .theme_tone import ToneSpec


def build_surface_styles(
    p: ShellPalette,
    m: ShellMetrics,
    accent: ToneSpec,
    success: ToneSpec,
    warning: ToneSpec,
    error: ToneSpec,
    muted: ToneSpec,
) -> str:
    return f"""
        QWidget {{
            color: {p.text};
            font-size: 13px;
        }}
        QFrame#windowShell {{
            background: {p.window_shell_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.window_radius}px;
        }}
        QFrame#card, QFrame#panelCard {{
            background: {p.card_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.card_radius}px;
        }}
        QFrame#subtlePanel {{
            background: {p.surface_subtle};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame#statusCard {{
            background: {p.status_card_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.card_radius}px;
        }}
        QFrame#statusPanel {{
            background: {p.status_panel_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame[surfaceRole="card"], QWidget[surfaceRole="card"] {{
            background: {p.card_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.card_radius}px;
        }}
        QFrame[surfaceRole="panel"], QWidget[surfaceRole="panel"] {{
            background: {p.surface_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame[surfaceRole="subtle"], QWidget[surfaceRole="subtle"] {{
            background: {p.surface_subtle};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame[surfaceRole="content"], QWidget[surfaceRole="content"] {{
            background: {p.content_bg};
            border: none;
            border-radius: 0;
        }}
        QFrame[surfaceRole="status"], QWidget[surfaceRole="status"] {{
            background: {p.status_panel_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame[surfaceRole="card"][tone="accent"], QWidget[surfaceRole="card"][tone="accent"],
        QFrame[surfaceRole="panel"][tone="accent"], QWidget[surfaceRole="panel"][tone="accent"],
        QFrame[surfaceRole="subtle"][tone="accent"], QWidget[surfaceRole="subtle"][tone="accent"],
        QFrame[surfaceRole="status"][tone="accent"], QWidget[surfaceRole="status"][tone="accent"] {{
            background: {accent.fill};
            border: 1px solid {accent.border};
        }}
        QFrame[surfaceRole="card"][tone="success"], QWidget[surfaceRole="card"][tone="success"],
        QFrame[surfaceRole="panel"][tone="success"], QWidget[surfaceRole="panel"][tone="success"],
        QFrame[surfaceRole="subtle"][tone="success"], QWidget[surfaceRole="subtle"][tone="success"],
        QFrame[surfaceRole="status"][tone="success"], QWidget[surfaceRole="status"][tone="success"] {{
            background: {success.fill};
            border: 1px solid {success.border};
        }}
        QFrame[surfaceRole="card"][tone="warning"], QWidget[surfaceRole="card"][tone="warning"],
        QFrame[surfaceRole="panel"][tone="warning"], QWidget[surfaceRole="panel"][tone="warning"],
        QFrame[surfaceRole="subtle"][tone="warning"], QWidget[surfaceRole="subtle"][tone="warning"],
        QFrame[surfaceRole="status"][tone="warning"], QWidget[surfaceRole="status"][tone="warning"] {{
            background: {warning.fill};
            border: 1px solid {warning.border};
        }}
        QFrame[surfaceRole="card"][tone="error"], QWidget[surfaceRole="card"][tone="error"],
        QFrame[surfaceRole="panel"][tone="error"], QWidget[surfaceRole="panel"][tone="error"],
        QFrame[surfaceRole="subtle"][tone="error"], QWidget[surfaceRole="subtle"][tone="error"],
        QFrame[surfaceRole="status"][tone="error"], QWidget[surfaceRole="status"][tone="error"] {{
            background: {error.fill};
            border: 1px solid {error.border};
        }}
        QWidget[transparentSurface="true"], QFrame[transparentSurface="true"] {{
            background: transparent;
            border: none;
        }}
    """
