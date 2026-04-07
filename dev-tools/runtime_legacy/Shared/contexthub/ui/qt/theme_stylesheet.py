from __future__ import annotations

from pathlib import Path

from .theme_metrics import get_shell_metrics
from .theme_palette import get_shell_palette
from .theme_stylesheet_buttons import build_button_styles
from .theme_stylesheet_controls import build_control_styles
from .theme_stylesheet_scroll import build_scroll_styles
from .theme_stylesheet_surface import build_surface_styles
from .theme_stylesheet_text import build_text_styles
from .theme_tone import get_tone_spec


def build_shell_stylesheet() -> str:
    p = get_shell_palette()
    m = get_shell_metrics()
    combo_arrow = (Path(__file__).resolve().parent / "assets" / "combo_chevron_down.svg").as_posix()
    accent = get_tone_spec("accent", p)
    success = get_tone_spec("success", p)
    warning = get_tone_spec("warning", p)
    error = get_tone_spec("error", p)
    muted = get_tone_spec("muted", p)
    return (
        build_surface_styles(p, m, accent, success, warning, error, muted)
        + build_text_styles(p, accent, success, warning, error, muted)
        + build_button_styles(p, m)
        + build_control_styles(p, m)
        + build_scroll_styles(combo_arrow)
    )
