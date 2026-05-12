"""Cross-thread service-to-UI signal bridge.

Background services (running on a worker thread or a thread-pool
executor) need a way to push update payloads to the Qt main thread.
The pattern repeated across video / audio / subtitle services was:

    class ServiceBridge(QObject):
        updated = Signal(dict)
        def emit_update(self, **payload):
            self.updated.emit(payload)

Hoist it once so new background-service apps don't reinvent the wheel
and accidentally do something thread-unsafe.

Usage::

    self.service_bridge = ServiceBridge()
    self.service_bridge.updated.connect(self._on_service_update)
    self.service = MyService(self.state, on_update=self.service_bridge.emit_update)

The Qt queued-connection across thread boundaries guarantees that
``_on_service_update`` runs on the GUI thread.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class ServiceBridge(QObject):
    """Forwards background-service update events to a Qt signal."""

    updated = Signal(dict)

    def emit_update(self, **payload) -> None:
        self.updated.emit(payload)


__all__ = ["ServiceBridge"]
