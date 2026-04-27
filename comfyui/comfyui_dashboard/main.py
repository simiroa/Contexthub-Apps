from __future__ import annotations

import sys
import shutil
import subprocess
import webbrowser
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime
from contexthub.utils.startup_errors import format_startup_error

ENGINE_ROOT = APP_ROOT.parent / "_engine"
SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (ENGINE_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    qt_t,
)
from manager.helpers.comfyui_service import ComfyUIService

try:
    from PySide6.QtCore import QThread, QTimer, Signal, Qt
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit(format_startup_error(exc)) from exc


APP_TITLE = qt_t("comfyui.dashboard.title", "ComfyUI Dashboard")
APP_SUBTITLE = qt_t("comfyui.dashboard.subtitle", "Mini Qt control surface for ComfyUI")


class TaskThread(QThread):
    finished_with_result = Signal(bool, str, object)

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def run(self) -> None:
        result = self._callback()
        if isinstance(result, tuple):
            if len(result) == 3:
                ok, message, payload = result
            elif len(result) == 2:
                ok, message = result
                payload = None
            else:
                ok, message, payload = bool(result), "Completed", None
        else:
            ok, message, payload = bool(result), "Completed", None
        self.finished_with_result.emit(ok, message, payload)


class DashboardWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.service = ComfyUIService()
        self._task_thread: TaskThread | None = None
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(2000)
        self._refresh_timer.timeout.connect(self.refresh_status)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(560, 320)
        self.setMinimumSize(520, 300)
        apply_app_icon(self, APP_ROOT)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self.refresh_status()
        self._refresh_timer.start()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        central.setObjectName("centralHost")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(m.section_gap)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        self.window_shell.setAttribute(Qt.WA_StyledBackground, True)
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, APP_ROOT, show_webui=True)
        self.header_surface.asset_count_badge.show()
        self.header_surface.runtime_status_badge.show()
        self.header_surface.open_webui_btn.hide()
        shell_layout.addWidget(self.header_surface)

        self.content_card = QFrame()
        self.content_card.setObjectName("card")
        content_layout = QVBoxLayout(self.content_card)
        content_layout.setContentsMargins(m.card_padding, m.card_padding, m.card_padding, m.card_padding)
        content_layout.setSpacing(m.section_gap)

        self.gpu_summary = QLabel("GPU: detecting...")
        self.gpu_summary.setObjectName("summaryText")
        self.gpu_summary.setWordWrap(True)
        content_layout.addWidget(self.gpu_summary)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.open_web_btn = QPushButton("Open Web UI")
        for btn in (self.start_btn, self.stop_btn, self.open_web_btn):
            btn.setMinimumHeight(32)
            action_row.addWidget(btn, 1)
        content_layout.addLayout(action_row)

        shell_layout.addWidget(self.content_card, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)

        root.addWidget(self.window_shell)

        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)
        self.open_web_btn.clicked.connect(self.open_web_ui)

    def _set_busy(self, busy: bool) -> None:
        for btn in (
            self.start_btn,
            self.stop_btn,
            self.open_web_btn,
        ):
            btn.setEnabled(not busy)

    def _run_task(self, callback, done_label: str) -> None:
        if self._task_thread and self._task_thread.isRunning():
            QMessageBox.information(self, APP_TITLE, "Another action is already running.")
            return

        self._set_busy(True)
        self._task_thread = TaskThread(callback)
        self._task_thread.finished_with_result.connect(
            lambda ok, msg, payload: self._finish_task(ok, msg, payload, done_label)
        )
        self._task_thread.start()

    def _finish_task(self, ok: bool, message: str, payload: object, done_label: str) -> None:
        self._set_busy(False)
        self.refresh_status()

    def _server_address(self) -> str:
        address = getattr(self.service.client, "server_address", "")
        if address:
            return address
        host = getattr(self.service.client, "host", "127.0.0.1")
        port = getattr(self.service.client, "port", self.service.port)
        return f"http://{host}:{port}"

    def refresh_status(self) -> None:
        running, port = self.service.is_running()
        self.header_surface.asset_count_badge.setText(str(port or self.service.port))
        self.header_surface.runtime_status_badge.setText("READY" if running else "STOPPED")
        self.gpu_summary.setText(self._read_gpu_summary())
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def start_server(self) -> None:
        self._run_task(lambda: self.service.ensure_running(start_if_missing=True), "Start")

    def stop_server(self) -> None:
        self._run_task(lambda: self.service.stop(only_if_owned=False), "Stop")

    def open_web_ui(self) -> None:
        url = self._server_address()
        webbrowser.open(url)
        self.refresh_status()

    def _read_gpu_summary(self) -> str:
        if shutil.which("nvidia-smi"):
            try:
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                line = (result.stdout or "").strip().splitlines()[0]
                parts = [part.strip() for part in line.split(",")]
                if len(parts) >= 4:
                    name = parts[0]
                    total_gb = float(parts[1]) / 1024.0
                    used_gb = float(parts[2]) / 1024.0
                    util = parts[3]
                    return f"GPU: {name} | VRAM: {used_gb:.1f}/{total_gb:.1f} GB | Load: {util}%"
            except Exception:
                pass
        try:
            import torch

            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                total_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
                return f"GPU: {name} | VRAM: live stats unavailable | Total: {total_gb:.1f} GB"
        except Exception:
            pass
        return "GPU: unavailable"

def main() -> int:
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
