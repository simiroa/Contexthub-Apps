import json
import os
import subprocess
import time
from pathlib import Path

from core.logger import setup_logger
from core.paths import LOGS_DIR
from manager.helpers.comfyui_client import ComfyUIManager

logger = setup_logger("comfyui_service")

STATE_FILE = LOGS_DIR / "comfyui_state.json"
LOCK_FILE = LOGS_DIR / "comfyui_state.lock"
LOG_FILE = LOGS_DIR / "comfyui_server.log"

LOCK_STALE_SECONDS = 120
LOCK_WAIT_SECONDS = 12
STATE_FRESH_SECONDS = 10


def _ensure_logs_dir():
    LOGS_DIR.mkdir(exist_ok=True, parents=True)


def _load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state):
    _ensure_logs_dir()
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.debug(f"State write failed: {exc}")


def _update_state(**updates):
    state = _load_state()
    state.update(updates)
    _save_state(state)
    return state


def _lock_is_stale():
    if not LOCK_FILE.exists():
        return False
    try:
        age = time.time() - LOCK_FILE.stat().st_mtime
        return age > LOCK_STALE_SECONDS
    except Exception:
        return False


def _acquire_lock(timeout=LOCK_WAIT_SECONDS, poll=0.25):
    _ensure_logs_dir()
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _lock_is_stale():
            try:
                LOCK_FILE.unlink()
            except Exception:
                pass
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            return True
        except FileExistsError:
            time.sleep(poll)
        except Exception:
            time.sleep(poll)
    return False


def _release_lock():
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def _is_pid_running(pid):
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        try:
            output = subprocess.check_output(
                f"tasklist /FI \"PID eq {pid}\"",
                shell=True,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            return str(pid) in output
        except Exception:
            return False


class ComfyUIService:
    def __init__(self, host="127.0.0.1", port=None):
        self.host = host
        self.port = port or 8190
        self.client = ComfyUIManager(host=host, port=self.port)

    def _apply_state_port(self, state):
        port = state.get("port")
        if port:
            self.client.set_active_port(port)
        return port

    def _is_state_fresh(self, state):
        last_seen = state.get("last_seen")
        if not last_seen:
            return False
        try:
            return (time.time() - float(last_seen)) <= STATE_FRESH_SECONDS
        except Exception:
            return False

    def is_running(self):
        state = _load_state()
        state_port = self._apply_state_port(state)
        state_pid = state.get("pid")
        if state.get("status") == "running":
            if state_pid and _is_pid_running(state_pid):
                port = state_port or self.client.port
                _update_state(last_seen=time.time(), port=port)
                return True, port
            if state_port and self._is_state_fresh(state):
                return True, state_port

        if self.client.is_running():
            port = self.client.port
            _update_state(status="running", port=port, last_seen=time.time())
            return True, port

        if state_port:
            return False, state_port
        return False, None

    def _wait_for_running(self, wait_seconds):
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            running, port = self.is_running()
            if running:
                return True, port, False
            time.sleep(1)
        return False, None, False

    def ensure_running(self, start_if_missing=True, wait_seconds=60):
        running, port = self.is_running()
        if running:
            return True, port, False
        if not start_if_missing:
            return False, None, False

        if not _acquire_lock():
            return self._wait_for_running(wait_seconds)

        try:
            running, port = self.is_running()
            if running:
                return True, port, False

            _update_state(
                status="starting",
                port=self.port,
                owner_pid=os.getpid(),
                started_at=time.time(),
            )

            ok = self.client.start(log_file=LOG_FILE)
            if ok:
                port = self.client.port
                _update_state(
                    status="running",
                    port=port,
                    pid=self.client.process.pid if self.client.process else None,
                    owner_pid=os.getpid(),
                    started_at=time.time(),
                    last_seen=time.time(),
                )
                return True, port, True

            _update_state(status="stopped", port=self.port)
            return False, None, False
        finally:
            _release_lock()

    def stop(self, only_if_owned=True):
        state = _load_state()
        owner_pid = state.get("owner_pid")
        if only_if_owned and not owner_pid:
            return False, "not_owned"

        port = state.get("port") or self.port
        if port:
            self.client.set_active_port(port)

        self.client.stop()
        _update_state(status="stopped")
        return True, "stopped"

    def force_kill_all(self):
        ComfyUIManager.kill_all_instances()
        _update_state(status="stopped")
        return True

    def open_console(self):
        _ensure_logs_dir()
        state = _load_state()
        console_pid = state.get("console_pid")
        if console_pid and _is_pid_running(console_pid):
            return True, "already_open"

        try:
            if not LOG_FILE.exists():
                LOG_FILE.write_text("", encoding="utf-8")
        except Exception:
            pass

        cmd = [
            "powershell",
            "-NoExit",
            "-Command",
            f"Get-Content -Path \"{str(LOG_FILE)}\" -Wait",
        ]
        proc = subprocess.Popen(cmd, creationflags=0x00000010)
        _update_state(console_pid=proc.pid)
        return True, "opened"

    def close_console(self):
        state = _load_state()
        console_pid = state.get("console_pid")
        if not console_pid:
            return False, "not_running"

        if _is_pid_running(console_pid):
            subprocess.run(
                f"taskkill /T /F /PID {console_pid}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        _update_state(console_pid=None)
        return True, "closed"
