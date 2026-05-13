"""Unified Qt app launcher for Contexthub apps.

Every app's ``start_app`` function previously implemented its own
combination of:

- ``QApplication.instance() or QApplication(sys.argv)``
- Splash painting (added in the Phase 1 startup pass)
- ``SingleInstance`` check + handoff of CLI targets
- Window construction
- ``window.show()`` / ``finish_splash(...)`` / ``app.exec()``

We hoist that flow into one helper so new apps don't reinvent it and
existing apps shrink. Apps that need a more bespoke flow can still call
the building blocks directly.

Usage::

    def start_app(targets, app_root):
        return launch_qt_app(
            app_id=APP_ID,
            app_root=app_root,
            window_factory=lambda: MyWindow(MyService(), app_root, targets),
            targets=targets,
            single_instance=True,
            splash=True,
        )

Or, when the window needs the SingleInstance object (e.g. to wire up
``handle_external_targets``)::

    def start_app(targets, app_root):
        def make_window(*, single_instance):
            window = MyWindow(MyService(), app_root, targets)
            if single_instance is not None:
                single_instance.message_received.connect(
                    window.handle_external_targets
                )
                window._si = single_instance  # keep alive
            return window

        return launch_qt_app(
            app_id=APP_ID,
            app_root=app_root,
            window_factory=make_window,
            targets=targets,
        )

The ``window_factory`` may accept a ``single_instance`` keyword if it
wants the helper to hand it the live ``SingleInstance``; otherwise the
helper just calls ``window_factory()`` with no arguments.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from PySide6.QtWidgets import QApplication


def launch_qt_app(
    *,
    app_id: str,
    app_root: str | Path,
    window_factory: Callable[..., Any],
    targets: Sequence[str] | None = None,
    single_instance: bool = True,
    splash: bool = True,
) -> int:
    """Run a Contexthub Qt app to completion.

    Returns the exit code from ``QApplication.exec()``, or ``0`` when a
    secondary instance hands off to the primary and exits.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    app_root_path = Path(app_root)

    si = None
    if single_instance:
        try:
            from .single_instance import SingleInstance  # noqa: PLC0415
            si = SingleInstance(app_id)
            if si.is_already_running():
                if targets:
                    si.send_to_primary(list(targets))
                return 0
        except Exception:
            si = None

    splash_obj = None
    finish_splash = lambda *_: None  # type: ignore[assignment]
    if splash:
        try:
            from .splash import show_splash, finish_splash as _finish  # noqa: PLC0415
            splash_obj = show_splash(app_root_path)
            finish_splash = _finish
        except Exception:
            splash_obj = None

    # Build the window. If the factory accepts a ``single_instance``
    # kwarg, hand it the live SingleInstance so it can wire signals.
    factory_kwargs: dict[str, Any] = {}
    try:
        sig = inspect.signature(window_factory)
        if "single_instance" in sig.parameters:
            factory_kwargs["single_instance"] = si
    except (TypeError, ValueError):
        pass
    window = window_factory(**factory_kwargs)

    # Start the IPC server only after the window exists, so external
    # target messages have somewhere to land.
    if si is not None and "single_instance" not in factory_kwargs:
        # Caller didn't take ownership; we wire up a default if the
        # window exposes handle_external_targets.
        try:
            si.start_server()
            if hasattr(window, "handle_external_targets"):
                si.message_received.connect(window.handle_external_targets)
            window._si = si  # keep alive
        except Exception:
            pass
    elif si is not None:
        # Caller took ownership in the factory; just start the server.
        try:
            si.start_server()
        except Exception:
            pass

    window.show()
    finish_splash(splash_obj, window)
    return app.exec()


__all__ = ["launch_qt_app"]
