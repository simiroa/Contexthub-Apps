from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShellPalette:
    app_bg: str = "#12161b"
    surface_bg: str = "#181d24"
    surface_subtle: str = "#161b21"
    surface_subtle_ghost: str = "rgba(255, 255, 255, 0.05)"
    content_bg: str = "#181d24"
    field_bg: str = "#14191f"
    border: str = "#2a3440"
    accent: str = "#3A82FF"
    accent_soft: str = "rgba(58, 130, 255, 0.15)"
    accent_text: str = "#FFFFFF"
    text: str = "#F2F5F8"
    text_muted: str = "#A7B0BA"
    muted: str = "#A7B0BA"
    accent_hover: str = "#66a0ff"
    success: str = "#5e9777"
    warning: str = "#b49563"
    error: str = "#b87379"
    error_soft: str = "rgba(184, 115, 121, 0.18)"
    control_bg: str = "#1d242d"
    control_border: str = "rgba(255,255,255,0.11)"
    window_shell_bg: str = "#141920"
    card_bg: str = "#1a2028"
    status_card_bg: str = "#1c232c"
    status_panel_bg: str = "#161b21"
    button_bg: str = "rgba(255,255,255,0.05)"
    button_hover: str = "rgba(255,255,255,0.09)"
    button_pressed: str = "rgba(255,255,255,0.12)"
    chrome_bg: str = "rgba(255,255,255,0.05)"
    chrome_hover: str = "rgba(255,255,255,0.12)"
    chip_bg: str = "rgba(75, 141, 255, 0.14)"
    chip_border: str = "rgba(75, 141, 255, 0.30)"
    chip_text: str = "#DCE8FF"


def get_shell_palette() -> ShellPalette:
    return ShellPalette()
