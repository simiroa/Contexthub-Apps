from __future__ import annotations

from contexthub.ui.flet.tokens import COLORS, WINDOWS


def apply_desktop_window(page, title: str, profile: str = "desktop", *, width: int | None = None, height: int | None = None):
    import flet as ft

    window = WINDOWS.get(profile, WINDOWS["desktop"])

    page.title = title
    page.padding = 0
    page.bgcolor = COLORS["app_bg"]
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = width or window["width"]
    page.window_height = height or window["height"]
    page.window_min_width = window["min_width"]
    page.window_min_height = window["min_height"]
