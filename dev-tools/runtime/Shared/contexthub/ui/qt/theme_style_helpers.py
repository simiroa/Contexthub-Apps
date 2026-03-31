from __future__ import annotations

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt theme runtime.") from exc


def qt_t(_key: str, default: str, **kwargs) -> str:
    try:
        return default.format(**kwargs)
    except Exception:
        return default


def _refresh_widget_style(widget: QWidget) -> None:
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_surface_role(widget: QWidget, role: str = "card", tone: str = "default") -> None:
    widget.setProperty("surfaceRole", role)
    widget.setProperty("tone", tone)
    _refresh_widget_style(widget)


def set_button_role(widget: QWidget, role: str = "secondary", tone: str = "default") -> None:
    widget.setProperty("buttonRole", role)
    widget.setProperty("tone", tone)
    _refresh_widget_style(widget)


def set_badge_role(widget: QWidget, role: str = "chip", tone: str = "accent") -> None:
    widget.setProperty("badgeRole", role)
    widget.setProperty("tone", tone)
    _refresh_widget_style(widget)


def set_transparent_surface(widget: QWidget) -> None:
    widget.setAttribute(Qt.WA_StyledBackground, True)
    widget.setProperty("transparentSurface", True)
    _refresh_widget_style(widget)
