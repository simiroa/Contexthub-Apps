from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QPushButton

from contexthub.ui.qt.shell import set_button_role
from shared._engine.components.icon_utils import get_icon


def build_icon_button(
    text: str,
    icon_name: str | None = None,
    role: str = "primary",
    is_icon_only: bool = False
) -> QPushButton:
    """
    Creates a standardized QPushButton infused with an optional Lucide SVG icon.
    Automatically applies the context hub 'role' style and colors the icon to match.
    
    Args:
        text: Text to display on the button (or tooltip if is_icon_only is True).
        icon_name: The name of the lucide SVG (e.g., "play", "trash-2").
        role: Button role ("primary", "secondary", "ghost", "danger", etc.).
        is_icon_only: If True, hides text and sets it as the native tooltip.
    """
    if is_icon_only or not text:
        button = QPushButton()
        if text:
            button.setToolTip(text)
    else:
        button = QPushButton(f" {text}" if icon_name else text)

    if icon_name:
        # Determine the color to blend the icon naturally against the button background
        icon_color = "#ffffff" if role in ("primary", "danger", "success") else "#94a3b8"
        button.setIcon(get_icon(icon_name, color=icon_color))
        
        # Determine icon size based on button type
        if not text or is_icon_only:
            sz = QSize(*button.m.icon_size_sm) if hasattr(button, 'm') else QSize(18, 18)
        else:
            sz = QSize(*button.m.icon_size_sm) if hasattr(button, 'm') else QSize(16, 16)
        button.setIconSize(sz)

    button.setObjectName(role)
    set_button_role(button, role)
    
    # Force alignment for iconic buttons
    if not text or is_icon_only:
        button.setFixedSize(26, 26) # Match shell metrics input_min_height
    
    return button
