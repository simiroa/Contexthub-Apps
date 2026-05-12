from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

class SingleInstance(QObject):
    """
    Handles single instance logic for Contexthub apps.
    If another instance is already running, it passes the targets to it and exits.
    """
    message_received = Signal(list)  # Emitted when new targets are received from another instance

    def __init__(self, app_id: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.app_id = app_id
        self.server_name = f"contexthub_{app_id}"
        self._server: QLocalServer | None = None

    def is_already_running(self) -> bool:
        """Checks if another instance is running by trying to connect to the local server."""
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if socket.waitForConnected(500):
            socket.close()
            return True
        return False

    def send_to_primary(self, targets: list[str]) -> bool:
        """Sends target files to the primary instance and returns True if successful."""
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if socket.waitForConnected(500):
            data = json.dumps(targets).encode("utf-8")
            socket.write(data)
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            return True
        return False

    def start_server(self) -> bool:
        """Starts the local server to listen for targets from secondary instances."""
        # Cleanup existing socket file if it exists (common on Unix/Linux, but good practice on Windows too)
        QLocalServer.removeServer(self.server_name)
        
        self._server = QLocalServer(self)
        if not self._server.listen(self.server_name):
            return False
            
        self._server.newConnection.connect(self._on_new_connection)
        return True

    def _on_new_connection(self) -> None:
        if not self._server:
            return
            
        socket = self._server.nextPendingConnection()
        if not socket:
            return
            
        if socket.waitForReadyRead(1000):
            data = socket.readAll().data()
            try:
                targets = json.loads(data.decode("utf-8"))
                if isinstance(targets, list):
                    self.message_received.emit(targets)
            except Exception:
                pass
        
        socket.disconnectFromServer()
