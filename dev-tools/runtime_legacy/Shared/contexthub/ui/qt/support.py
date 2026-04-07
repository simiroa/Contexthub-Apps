from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QWidget
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt shell runtime.") from exc


def runtime_settings_signature() -> str:
    return "default"


def refresh_runtime_preferences() -> None:
    return None


def resolve_app_icon(app_root: Path) -> Path | None:
    for name in ("icon.png", "icon.ico"):
        icon_path = app_root / name
        if icon_path.exists():
            return icon_path
    return None


def resolve_manual_path(app_root: Path) -> Path | None:
    manual_path = app_root / "manual.md"
    if manual_path.exists():
        return manual_path
    return None


def apply_app_icon(widget: QWidget, app_root: Path) -> None:
    icon_path = resolve_app_icon(app_root)
    if icon_path is not None:
        widget.setWindowIcon(QIcon(str(icon_path)))
