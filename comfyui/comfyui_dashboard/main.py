from __future__ import annotations

import sys
import shutil
import subprocess
import time
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
    set_button_role,
)
from manager.helpers.comfyui_service import ComfyUIService

try:
    from PySide6.QtCore import QThread, QTimer, Signal, Qt
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
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
        try:
            result = self._callback()
        except Exception as exc:
            self.finished_with_result.emit(False, str(exc), None)
            return
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
        self._status_thread: TaskThread | None = None
        self._status_running = False
        self._status_port = self.service.port
        self._status_state = "stopped"
        self._last_log_line = ""
        self._last_message = "Ready."
        self._current_task_label = ""
        self._gpu_summary_cache = "GPU: detecting..."
        self._last_gpu_probe = 0.0
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(3000)
        self._refresh_timer.timeout.connect(self.refresh_status)
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(1000)
        self._log_timer.timeout.connect(self._refresh_log_tail)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(680, 430)
        self.setMinimumSize(620, 390)
        apply_app_icon(self, APP_ROOT)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._apply_status_ui()
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

        self.status_line = QLabel("Ready.")
        self.status_line.setObjectName("summaryText")
        self.status_line.setWordWrap(True)
        content_layout.addWidget(self.status_line)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        content_layout.addWidget(self.progress_bar)

        self.log_tail = QLabel("Log: waiting for server output.")
        self.log_tail.setObjectName("summaryText")
        self.log_tail.setWordWrap(True)
        content_layout.addWidget(self.log_tail)

        node_row = QHBoxLayout()
        node_row.setSpacing(8)
        self.node_url_edit = QLineEdit()
        self.node_url_edit.setPlaceholderText("Custom node Git URL")
        self.install_node_btn = QPushButton("Install Node")
        set_button_role(self.install_node_btn, "secondary")
        self.install_node_btn.setMinimumHeight(32)
        node_row.addWidget(self.node_url_edit, 1)
        node_row.addWidget(self.install_node_btn, 0)
        content_layout.addLayout(node_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.open_web_btn = QPushButton("Open Web UI")
        for btn in (self.start_btn, self.stop_btn, self.open_web_btn):
            btn.setMinimumHeight(32)
            action_row.addWidget(btn, 1)
        content_layout.addLayout(action_row)

        manage_row = QHBoxLayout()
        manage_row.setSpacing(8)
        self.console_btn = QPushButton("Console")
        self.update_btn = QPushButton("Update")
        self.nodes_folder_btn = QPushButton("Nodes Folder")
        for btn in (self.console_btn, self.update_btn, self.nodes_folder_btn):
            set_button_role(btn, "secondary")
            btn.setMinimumHeight(32)
            manage_row.addWidget(btn, 1)
        content_layout.addLayout(manage_row)

        shell_layout.addWidget(self.content_card, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)

        root.addWidget(self.window_shell)

        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)
        self.open_web_btn.clicked.connect(self.open_web_ui)
        self.console_btn.clicked.connect(self.open_console)
        self.update_btn.clicked.connect(self.update_comfyui)
        self.install_node_btn.clicked.connect(self.install_custom_node)
        self.nodes_folder_btn.clicked.connect(self.open_nodes_folder)

    def _set_busy(self, busy: bool) -> None:
        for btn in (
            self.start_btn,
            self.stop_btn,
            self.open_web_btn,
            self.console_btn,
            self.update_btn,
            self.install_node_btn,
            self.nodes_folder_btn,
        ):
            btn.setEnabled(not busy)
        self.node_url_edit.setEnabled(not busy)
        self.progress_bar.setVisible(busy)
        if busy:
            self._log_timer.start()
        else:
            self._log_timer.stop()

    def _run_task(self, callback, done_label: str) -> None:
        if self._task_thread and self._task_thread.isRunning():
            QMessageBox.information(self, APP_TITLE, "Another action is already running.")
            return

        self._current_task_label = done_label
        self._last_message = f"{done_label} running..."
        self.status_line.setText(self._last_message)
        self.header_surface.runtime_status_badge.setText("BUSY")
        self._set_busy(True)
        self._task_thread = TaskThread(callback)
        self._task_thread.finished_with_result.connect(
            lambda ok, msg, payload: self._finish_task(ok, msg, payload, done_label)
        )
        self._task_thread.start()

    def _finish_task(self, ok: bool, message: str, payload: object, done_label: str) -> None:
        detail = message or ("Completed." if ok else "Failed.")
        self._last_message = f"{done_label}: {detail}"
        self.status_line.setText(self._last_message)
        self._set_busy(False)
        self.refresh_status()
        self._refresh_log_tail()
        if not ok:
            QMessageBox.warning(self, APP_TITLE, self._last_message)

    def _server_address(self) -> str:
        address = getattr(self.service.client, "server_address", "")
        if address:
            return address
        host = getattr(self.service.client, "host", "127.0.0.1")
        port = getattr(self.service.client, "port", self.service.port)
        return f"http://{host}:{port}"

    def refresh_status(self) -> None:
        self._apply_status_ui()
        if self._status_thread and self._status_thread.isRunning():
            return

        now = time.monotonic()
        include_gpu = self._gpu_summary_cache == "GPU: detecting..." or (now - self._last_gpu_probe) >= 15.0
        self._status_thread = TaskThread(lambda: self._read_status_snapshot(include_gpu))
        self._status_thread.finished_with_result.connect(self._finish_status_probe)
        self._status_thread.start()

    def _read_status_snapshot(self, include_gpu: bool):
        snapshot = self.service.status_snapshot()
        gpu = self._read_gpu_summary() if include_gpu else None
        snapshot["gpu"] = gpu
        return True, "status", snapshot

    def _finish_status_probe(self, ok: bool, message: str, payload: object) -> None:
        if isinstance(payload, dict):
            self._status_running = bool(payload.get("running"))
            self._status_port = payload.get("port") or self.service.port
            self._status_state = str(payload.get("status") or ("running" if self._status_running else "stopped"))
            self._last_log_line = str(payload.get("last_log") or self._last_log_line)
            gpu = payload.get("gpu")
            if gpu:
                self._gpu_summary_cache = str(gpu)
                self._last_gpu_probe = time.monotonic()
        self._apply_status_ui()

    def _apply_status_ui(self) -> None:
        self.header_surface.asset_count_badge.setText(str(self._status_port or self.service.port))
        if self._task_thread and self._task_thread.isRunning():
            status_text = "BUSY"
        elif self._status_running:
            status_text = "READY"
        elif self._status_state == "starting":
            status_text = "STARTING"
        else:
            status_text = "STOPPED"
        self.header_surface.runtime_status_badge.setText(status_text)
        self.gpu_summary.setText(self._gpu_summary_cache)
        self.status_line.setText(self._last_message)
        if self._last_log_line:
            self.log_tail.setText(f"Log: {self._last_log_line}")
        if not (self._task_thread and self._task_thread.isRunning()):
            self.start_btn.setEnabled(not self._status_running)
            self.stop_btn.setEnabled(self._status_running)
            for btn in (self.open_web_btn, self.console_btn, self.update_btn, self.install_node_btn, self.nodes_folder_btn):
                btn.setEnabled(True)
            self.node_url_edit.setEnabled(True)

    def start_server(self) -> None:
        self._run_task(self._start_server_task, "Start")

    def _start_server_task(self):
        ok, port, started = self.service.ensure_running(start_if_missing=True)
        if ok:
            verb = "Started" if started else "Already running"
            return True, f"{verb} on port {port}.", {"port": port}
        last_log = self.service.read_last_log_line()
        message = "ComfyUI did not become ready before timeout."
        if last_log:
            message = f"{message} Last log: {last_log}"
        return False, message, None

    def stop_server(self) -> None:
        self._run_task(lambda: self.service.stop(only_if_owned=False), "Stop")

    def open_web_ui(self) -> None:
        url = self._server_address()
        webbrowser.open(url)
        self.refresh_status()

    def open_console(self) -> None:
        ok, message = self.service.open_console()
        self._last_message = f"Console: {message}"
        self.status_line.setText(self._last_message)
        if not ok:
            QMessageBox.warning(self, APP_TITLE, self._last_message)

    def update_comfyui(self) -> None:
        self._run_task(lambda: self.service.update_comfyui(update_nodes=True), "Update")

    def install_custom_node(self) -> None:
        repo_url = self.node_url_edit.text().strip()
        self._run_task(lambda: self.service.install_custom_node(repo_url), "Install node")

    def open_nodes_folder(self) -> None:
        ok, message = self.service.open_custom_nodes_folder()
        self._last_message = f"Nodes Folder: {message}"
        self.status_line.setText(self._last_message)
        if not ok:
            QMessageBox.warning(self, APP_TITLE, self._last_message)

    def _refresh_log_tail(self) -> None:
        line = self.service.read_last_log_line()
        if line:
            self._last_log_line = line
            self.log_tail.setText(f"Log: {line}")

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
