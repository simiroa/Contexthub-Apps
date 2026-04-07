import base64
from typing import Optional

try:
    from PySide6.QtWidgets import QWidget
except ImportError:
    # Fallback for environments without PySide6
    class QWidget: pass


def qt_t(text: str, fallback: str | None = None, **kwargs) -> str:
    """
    Compatibility translation helper.

    Legacy callers pass a single text string.
    Newer callers pass (key, fallback). Until a real translation layer is
    wired in here, return the fallback when present, otherwise the original text.
    """
    return fallback if fallback is not None else text


def set_button_role(widget: QWidget, role: str) -> None:
    """Sets the custom 'buttonRole' property for QSS selector logic."""
    widget.setProperty("buttonRole", role)
    if hasattr(widget, "style"):
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def set_badge_role(widget: QWidget, *args) -> None:
    """
    Sets the custom 'badgeRole' property for QSS selector logic.
    Supports both legacy (widget, role) and (widget, property_name, role) patterns.
    """
    if not args:
        return
    role = args[-1]
    widget.setProperty("badgeRole", role)
    if hasattr(widget, "style"):
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def set_surface_role(widget: QWidget, role: str) -> None:
    """Sets the custom 'surfaceRole' property for QSS selector logic."""
    widget.setProperty("surfaceRole", role)
    if hasattr(widget, "style"):
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def set_transparent_surface(widget: QWidget, transparent: bool = True) -> None:
    """Sets the custom 'transparent' property for QSS selector logic."""
    widget.setProperty("transparent", transparent)
    if hasattr(widget, "style"):
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def get_svg_chevron_data_uri(direction: str = "down", color: Optional[str] = None) -> str:
    """
    Generates a base64 encoded SVG data URI for a chevron arrow.
    direction can be: "up", "down", "left", "right"
    """
    if color is None:
        try:
            # Inline import to avoid circular dependency with theme_palette
            from contexthub.ui.qt.theme_palette import get_shell_palette
            p = get_shell_palette()
            color = p.text_muted
        except:
            color = "#a1a1aa" # fallback gray
    
    # Points according to direction
    points = "6 9 12 15 18 9" # down
    if direction == "up":
        points = "18 15 12 9 6 15"
    elif direction == "left":
        points = "15 18 9 12 15 6"
    elif direction == "right":
        points = "9 6 15 12 9 18"
        
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' 
    stroke='{color}' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>
    <polyline points='{points}'></polyline></svg>"""
    
    b64_svg = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{b64_svg}"
