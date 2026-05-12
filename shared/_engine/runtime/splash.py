"""Lightweight splash helper for app startup.

Shows a small pixmap (typically the app icon) right after QApplication is
created, so the user gets an immediate visual response while the rest of the
window is being built. Use `finish_splash(splash, window)` when the main
window is shown.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen


def show_splash(app_root: str | Path, size: int = 128) -> Optional[QSplashScreen]:
    """Show a small splash using the app's icon. Returns None if unavailable."""
    try:
        app_root = Path(app_root)
        icon_path = app_root / "icon.png"
        if not icon_path.exists():
            icon_path = app_root / "icon.ico"
        if not icon_path.exists():
            return None
        pix = QPixmap(str(icon_path))
        if pix.isNull():
            return None
        pix = pix.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        # Force one paint cycle so the user actually sees the splash before
        # the main window construction blocks the event loop.
        QApplication.processEvents()
        return splash
    except Exception:
        return None


def finish_splash(splash: Optional[QSplashScreen], window) -> None:
    if splash is None:
        return
    try:
        splash.finish(window)
    except Exception:
        pass
