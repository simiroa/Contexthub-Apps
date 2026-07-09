import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

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


def _run_command(command, cwd=None, timeout=120):
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part and part.strip())
        return result.returncode == 0, output.strip()
    except FileNotFoundError:
        return False, f"{command[0]} is not installed or not in PATH."
    except subprocess.TimeoutExpired:
        return False, f"{command[0]} command timed out after {timeout} seconds."
    except Exception as exc:
        return False, str(exc)


def _repo_folder_name(repo_url):
    parsed = urlparse(repo_url.strip())
    name = Path(parsed.path.rstrip("/")).name if parsed.path else ""
    if name.endswith(".git"):
        name = name[:-4]
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip(".-")
    return name or "custom-node"


def _tail_log_line(max_bytes=12000):
    if not LOG_FILE.exists():
        return ""
    try:
        with LOG_FILE.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            data = handle.read().decode("utf-8", errors="replace")
        for line in reversed(data.splitlines()):
            stripped = line.strip()
            if stripped:
                return stripped
    except Exception:
        return ""
    return ""


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

    def read_last_log_line(self):
        return _tail_log_line()

    def status_snapshot(self):
        running, port = self.is_running()
        state = _load_state()
        state_port = state.get("port") or port or self.service_port
        pid = state.get("pid")
        paths = self.runtime_paths()
        return {
            "running": running,
            "port": state_port,
            "status": state.get("status") or ("running" if running else "stopped"),
            "pid": pid,
            "pid_running": bool(pid and _is_pid_running(pid)),
            "last_log": self.read_last_log_line(),
            "paths": paths,
        }

    @property
    def service_port(self):
        return self.client.port or self.port

    def runtime_paths(self):
        comfy_dir = Path(getattr(self.client, "comfy_dir", ""))
        python_exe = Path(getattr(self.client, "python_exe", ""))
        main_py = getattr(self.client, "main_py_override", None) or (comfy_dir / "main.py")
        custom_nodes = comfy_dir / "custom_nodes"
        return {
            "comfy_dir": str(comfy_dir),
            "python_exe": str(python_exe),
            "main_py": str(main_py),
            "custom_nodes": str(custom_nodes),
            "comfy_exists": bool(Path(main_py).exists()),
            "python_exists": bool(python_exe.exists()),
            "custom_nodes_exists": bool(custom_nodes.exists()),
            "launcher": str(getattr(self.client, "launcher_path", "") or ""),
        }

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

    def update_comfyui(self, update_nodes=True):
        paths = self.runtime_paths()
        comfy_dir = Path(paths["comfy_dir"])
        if not paths["comfy_exists"]:
            return False, f"ComfyUI main.py not found: {paths['main_py']}", None
        if not (comfy_dir / ".git").exists():
            return False, f"ComfyUI is not a git checkout: {comfy_dir}", None
        ok, output = _run_command(["git", "pull", "--ff-only"], cwd=comfy_dir, timeout=180)
        if not ok:
            return False, f"ComfyUI update failed: {output}", None

        node_results = []
        if update_nodes:
            custom_nodes = Path(paths["custom_nodes"])
            if custom_nodes.exists():
                for node_dir in sorted(path for path in custom_nodes.iterdir() if path.is_dir()):
                    if not (node_dir / ".git").exists():
                        continue
                    node_ok, node_output = _run_command(["git", "pull", "--ff-only"], cwd=node_dir, timeout=120)
                    node_results.append((node_dir.name, node_ok, node_output))

        failed_nodes = [name for name, node_ok, _ in node_results if not node_ok]
        if failed_nodes:
            return False, f"ComfyUI updated, but custom node update failed: {', '.join(failed_nodes)}", node_results
        if node_results:
            return True, f"Updated ComfyUI and {len(node_results)} custom node repos.", node_results
        return True, "Updated ComfyUI.", node_results

    def install_custom_node(self, repo_url):
        repo_url = (repo_url or "").strip()
        if not repo_url:
            return False, "Enter a custom node Git URL.", None
        if not repo_url.startswith(("https://", "http://", "git@")):
            return False, "Custom node URL must be an http(s) or git URL.", None
        if not shutil.which("git"):
            return False, "Git is not installed or not in PATH.", None

        paths = self.runtime_paths()
        if not paths["comfy_exists"]:
            return False, f"ComfyUI main.py not found: {paths['main_py']}", None

        custom_nodes = Path(paths["custom_nodes"])
        custom_nodes.mkdir(parents=True, exist_ok=True)
        target = custom_nodes / _repo_folder_name(repo_url)

        if target.exists():
            if not (target / ".git").exists():
                return False, f"Target folder already exists and is not a git repo: {target}", None
            ok, output = _run_command(["git", "pull", "--ff-only"], cwd=target, timeout=180)
            action = "updated"
        else:
            ok, output = _run_command(["git", "clone", repo_url, str(target)], timeout=300)
            action = "installed"

        if not ok:
            return False, f"Custom node {action} failed: {output}", None

        requirements = target / "requirements.txt"
        pip_output = ""
        if requirements.exists():
            python_exe = Path(paths["python_exe"])
            if not python_exe.exists():
                return False, f"Node cloned, but Python was not found for requirements install: {python_exe}", str(target)
            pip_ok, pip_output = _run_command(
                [str(python_exe), "-m", "pip", "install", "-r", str(requirements)],
                cwd=target,
                timeout=600,
            )
            if not pip_ok:
                return False, f"Node cloned, but requirements install failed: {pip_output}", str(target)

        detail = f" Requirements installed." if pip_output else ""
        return True, f"Custom node {action}: {target.name}.{detail}", str(target)

    def open_custom_nodes_folder(self):
        paths = self.runtime_paths()
        custom_nodes = Path(paths["custom_nodes"])
        custom_nodes.mkdir(parents=True, exist_ok=True)
        os.startfile(str(custom_nodes))
        return True, str(custom_nodes)

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
