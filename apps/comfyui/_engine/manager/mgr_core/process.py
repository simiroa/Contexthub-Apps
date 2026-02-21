import sys
import os
import subprocess
import psutil
import json
import time
import socket
import logging
from pathlib import Path

logger = logging.getLogger("manager.core.process")

class TrayProcessManager:
    def __init__(self, root_dir: Path, settings: dict):
        self.root_dir = root_dir
        self.settings = settings
        self.pid_file = root_dir / "logs" / "tray_agent.pid"
        self.handshake_file = root_dir / "logs" / "tray_info.json"
        self.script_path = root_dir / "src" / "tray" / "agent.py"
        self.resolved_python = None

    def _find_free_port(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.bind(('', 0))
                return s.getsockname()[1]
        except:
            return 54321

    def _resolve_python_executable(self):
        """Resolve Python interpreter - prioritize embedded Python."""
        # Check embedded Python first
        embedded = self.root_dir / "tools" / "python" / "python.exe"
        if embedded.exists():
            return str(embedded)
        
        # Then check settings
        if self.settings.get("PYTHON_PATH"):
            py_path = Path(self.settings["PYTHON_PATH"])
            if py_path.exists():
                return str(py_path)
                
        # Fallback to current interpreter
        return sys.executable

    def is_running(self) -> bool:
        # Check handshake file for active status
        if self.handshake_file.exists():
            try:
                data = json.loads(self.handshake_file.read_text(encoding="utf-8"))
                pid = data.get("pid")
                if pid and psutil.pid_exists(pid):
                    return True
            except: pass
            
        # Fallback to PID file
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                if psutil.pid_exists(pid):
                    return True
            except: pass
            
        return False

    def start(self) -> tuple[bool, str]:
        if self.is_running():
            return True, "Already running"

        # Cleanup before start
        self.stop()
        
        python_exe = self._resolve_python_executable()
        port = self._find_free_port()
        
        cmd = [python_exe, str(self.script_path), "--port", str(port)]
        
        # Windows-specific: Hide console
        creationflags = 0x08000000 # CREATE_NO_WINDOW
        
        # If using python.exe, try to switch to pythonw.exe if available (optional)
        # But allow fallback to python.exe with CREATE_NO_WINDOW which works well.
        
        logger.info(f"Launching Tray Agent on port {port}: {cmd}")
        try:
            proc = subprocess.Popen(cmd, close_fds=True, creationflags=creationflags)
        except Exception as e:
            return False, f"Failed to launch process: {e}"

        # Wait for handshake
        timeout = 15.0  # Increased from 10.0s for robustness on slow systems
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.handshake_file.exists():
                try:
                    data = json.loads(self.handshake_file.read_text(encoding="utf-8"))
                    if data.get("status") == "ready" and data.get("pid") == proc.pid:
                        return True, "Tray Agent started successfully."
                except: pass
            if proc.poll() is not None:
                return False, f"Process exited immediately with code {proc.returncode}"
            time.sleep(0.2)
            
        # Timeout but process is still running?
        if proc.poll() is None:
            # User requested "Let it run" even if handshake is slow/missing
            logger.warning(f"Tray Agent (PID {proc.pid}) started but handshake file ({self.handshake_file}) not found within {timeout}s.")
            return True, "Tray Agent started (Handshake delayed/missing)."
            
        # Timeout and process dead
        self.stop() 
        return False, "Handshake timeout. Tray Agent failed to initialize."

    def stop(self) -> tuple[bool, str]:
        pid = None
        port = None
        
        # Try to get info from handshake
        if self.handshake_file.exists():
            try:
                data = json.loads(self.handshake_file.read_text(encoding="utf-8"))
                pid = data.get("pid")
                port = data.get("port")
            except: pass
            
        # Fallback to PID file
        if not pid and self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
            except: pass
            
        if not pid:
            # Maybe it's just a lingering handshake file without process
            if self.handshake_file.exists(): self.handshake_file.unlink(missing_ok=True)
            if self.pid_file.exists(): self.pid_file.unlink(missing_ok=True)
            return True, "Already stopped"

        # Soft stop via UDP
        if port:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(b"EXIT", ("127.0.0.1", port))
                sock.close()
                
                # Wait for exit
                for _ in range(10): # 2 seconds
                    if not psutil.pid_exists(pid):
                        break
                    time.sleep(0.2)
            except: pass
            
        # Hard kill if still alive
        if psutil.pid_exists(pid):
            try:
                p = psutil.Process(pid)
                p.terminate()
                try: p.wait(timeout=1)
                except: p.kill()
            except: pass
            
        # Cleanup files
        try: self.handshake_file.unlink(missing_ok=True)
        except: pass
        try: self.pid_file.unlink(missing_ok=True)
        except: pass
        
        return True, "Stopped"
