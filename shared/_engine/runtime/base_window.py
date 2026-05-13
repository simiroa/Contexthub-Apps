"""Base class for Contexthub Qt main windows.

Hoists the boilerplate that every ``QMainWindow`` subclass in this repo
was reimplementing identically: ``QSettings``-backed geometry restore,
the frameless + translucent flag block, accept-drops, runtime
preferences hot-reload, and the app icon hookup.

Usage::

    class MyWindow(BaseAppWindow):
        APP_ID = "my_app"

        def __init__(self, service, app_root, targets=None):
            super().__init__(app_root)
            self.service = service
            self._build_ui()
            self._restore_window_state()
            self._runtime_timer.start()

The subclass keeps full control over when state is restored and when
the hot-reload timer starts — typically right after ``_build_ui``.

What the base provides
----------------------

- ``self._settings`` — ``QSettings(self.SETTINGS_ORG, self.APP_ID)``.
- Frameless + translucent + accept-drops flags (toggle via kwargs).
- ``apply_app_icon(self, app_root)`` if the helper is importable.
- ``self._runtime_signature`` + ``self._runtime_timer`` (interval set,
  not started). Subclass typically calls ``.start()`` after ``_build_ui``.
- ``_restore_window_state`` / ``closeEvent`` / ``_check_runtime_preferences``
  methods that subclasses can rely on instead of redefining.

Optional hooks for subclasses
-----------------------------

- ``on_runtime_preferences_changed()`` — called after the stylesheet
  reapplies, when theme/language/etc. change at runtime.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import QMainWindow


class BaseAppWindow(QMainWindow):
    """See module docstring."""

    #: Subclasses MUST override.
    APP_ID: str = ""
    #: Org name used for QSettings; almost always "Contexthub".
    SETTINGS_ORG: str = "Contexthub"
    #: Interval in ms between runtime-preferences polls. ``0`` to disable.
    RUNTIME_HOT_RELOAD_MS: int = 1500

    def __init__(
        self,
        app_root: str | Path,
        *,
        frameless: bool = True,
        translucent: bool = True,
        accept_drops: bool = True,
    ) -> None:
        super().__init__()
        if not self.APP_ID:
            raise RuntimeError(
                f"{type(self).__name__} must set APP_ID at class level "
                "before subclassing BaseAppWindow."
            )

        self.app_root: Path = Path(app_root)
        self._settings = QSettings(self.SETTINGS_ORG, self.APP_ID)

        if frameless:
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        if translucent:
            self.setAttribute(Qt.WA_TranslucentBackground, True)
        if accept_drops:
            self.setAcceptDrops(True)

        # Best-effort icon application. Import lazily so the base class
        # remains usable in dev environments where the shared shell is
        # still resolving.
        try:
            from contexthub.ui.qt.shell import apply_app_icon  # noqa: PLC0415
            apply_app_icon(self, self.app_root)
        except Exception:
            pass

        self._runtime_signature: Any = None
        try:
            from contexthub.ui.qt.shell import runtime_settings_signature  # noqa: PLC0415
            self._runtime_signature = runtime_settings_signature()
        except Exception:
            pass

        self._runtime_timer = QTimer(self)
        if self.RUNTIME_HOT_RELOAD_MS > 0:
            self._runtime_timer.setInterval(self.RUNTIME_HOT_RELOAD_MS)
            self._runtime_timer.timeout.connect(self._check_runtime_preferences)

    # ------------------------------------------------------------------
    # Hooks the subclass can rely on or override.
    # ------------------------------------------------------------------

    def _restore_window_state(self) -> None:
        """Restore window geometry + maximized state from QSettings."""
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        if self._settings.value("is_maximized", False, bool):
            self.showMaximized()

    def _save_window_state(self) -> None:
        """Persist window geometry + maximized state to QSettings."""
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._save_window_state()
        super().closeEvent(event)

    def _check_runtime_preferences(self) -> None:
        """Poll runtime settings; if changed, reapply theme + notify."""
        try:
            from contexthub.ui.qt.shell import (  # noqa: PLC0415
                build_shell_stylesheet,
                refresh_runtime_preferences,
                runtime_settings_signature,
            )
        except Exception:
            return
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())
        if hasattr(self, "on_runtime_preferences_changed"):
            try:
                self.on_runtime_preferences_changed()
            except Exception:
                pass


__all__ = ["BaseAppWindow"]
