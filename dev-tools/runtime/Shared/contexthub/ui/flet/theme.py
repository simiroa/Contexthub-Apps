from __future__ import annotations

from contexthub.ui.flet.tokens import COLORS
from contexthub.ui.flet.window import apply_desktop_window


def configure_page(page, title: str, *, window_profile: str = "desktop"):
    import flet as ft

    apply_desktop_window(page, title, profile=window_profile)
    page.theme = ft.Theme(
        font_family="Segoe UI",
        color_scheme_seed=COLORS["accent"],
    )
    page.dark_theme = ft.Theme(
        font_family="Segoe UI",
        color_scheme_seed=COLORS["accent"],
    )
