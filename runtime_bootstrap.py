from __future__ import annotations

import atexit
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _candidate_shared_roots(app_root: Path) -> list[Path | None]:
    repo_root = app_root.parents[1]
    env_shared_runtime_root = os.environ.get("CTX_SHARED_RUNTIME_ROOT")
    env_shared_root = os.environ.get("CTX_SHARED_ROOT")
    return [
        Path(env_shared_runtime_root) if env_shared_runtime_root else None,
        Path(env_shared_root).parent if env_shared_root else None,
        repo_root.parent / "Contexthub" / "Runtimes" / "Shared",
        app_root.parent.parent / "Contexthub" / "Runtimes" / "Shared",
        app_root / "Runtimes" / "Shared",
        repo_root / "dev-tools" / "runtime" / "Shared",
    ]


def _candidate_runtime_roots(app_root: Path) -> list[Path | None]:
    repo_root = app_root.parents[1]
    env_runtime_root = os.environ.get("CTX_RUNTIME_ROOT")
    env_dev_runtime_root = os.environ.get("CTX_DEV_RUNTIME_ROOT")
    return [
        Path(env_runtime_root) if env_runtime_root else None,
        Path(env_dev_runtime_root) if env_dev_runtime_root else None,
        repo_root.parent / "Contexthub" / "Runtimes",
        app_root.parent.parent / "Contexthub" / "Runtimes",
        repo_root / "dev-tools" / "runtime",
    ]


def resolve_shared_runtime(app_root: str | Path) -> tuple[Path, Path]:
    app_root = Path(app_root).resolve()
    os.environ.setdefault("CTX_APP_ROOT", str(app_root))

    runtime_root: Path | None = None
    for candidate in _candidate_runtime_roots(app_root):
        if candidate is not None and candidate.exists():
            runtime_root = candidate.resolve()
            break

    if runtime_root is None:
        runtime_root = app_root.parents[1] / "dev-tools" / "runtime"

    shared_root: Path | None = None
    for candidate in _candidate_shared_roots(app_root):
        if candidate is not None and candidate.exists():
            shared_root = candidate.resolve()
            break

    if shared_root is None:
        shared_root = runtime_root / "Shared"

    shared_package_root = shared_root / "contexthub"
    return shared_root, shared_package_root


_ACTIVE_INSTANCE_LOCKS: list[object] = []


def _normalize_lock_name(app_root: Path) -> str:
    abs_path = str(app_root.resolve())
    path_hash = hashlib.md5(abs_path.encode()).hexdigest()[:8]
    relative_name = f"{app_root.parent.name}__{app_root.name}__{path_hash}"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", relative_name).strip("._-") or "contexthub_app"


def _release_instance_lock(lock_file, lock_path: Path) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        lock_file.close()
    except Exception:
        pass
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


def _read_lock_pid(lock_path: Path) -> int | None:
    try:
        text = lock_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for line in text:
        if line.startswith("pid="):
            try:
                return int(line.split("=", 1)[1].strip())
            except Exception:
                return None
    return None


def _kill_process_tree(pid: int) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _wait_for_process_exit(pid: int, timeout: float = 6.0) -> bool:
    if pid <= 0:
        return True
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            output = (result.stdout or "") + (result.stderr or "")
            if str(pid) not in output:
                return True
        except Exception:
            return True
        time.sleep(0.2)
    return False


def _acquire_instance_lock(app_root: Path):
    lock_dir = Path(tempfile.gettempdir()) / "contexthub-app-locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{_normalize_lock_name(app_root)}.lock"
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing_pid = _read_lock_pid(lock_path)
            if existing_pid is None:
                try:
                    lock_path.unlink(missing_ok=True)
                except Exception:
                    pass
                time.sleep(0.1)
                continue

            # NEW: Verify if recorded argv0 matches current sys.argv[0]
            # to prevent killing unrelated apps that might collide on simple lock names
            try:
                recorded_argv0 = ""
                for line in lock_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("argv0="):
                        recorded_argv0 = line.split("=", 1)[1].strip()
                
                if recorded_argv0 and recorded_argv0 != sys.argv[0]:
                    # Different app, but somehow lock name matched?
                    # This shouldn't happen with the new hash-based naming, but it's a safe fallback.
                    # We treat it as lock acquisition failure rather than killing the other app.
                    return None
            except Exception:
                pass

            _kill_process_tree(existing_pid)
            _wait_for_process_exit(existing_pid)
            try:
                lock_path.unlink(missing_ok=True)
            except Exception:
                pass
            time.sleep(0.1)
            continue
        except Exception:
            return None

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
                lock_file.write(f"pid={os.getpid()}\nargv0={sys.argv[0]}\n")
                lock_file.flush()
                os.fsync(lock_file.fileno())
            _ACTIVE_INSTANCE_LOCKS.append(lock_path)
            atexit.register(_release_instance_lock, None, lock_path)
            return lock_path
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                lock_path.unlink(missing_ok=True)
            except Exception:
                pass
            return None


def _should_enforce_single_instance() -> bool:
    if os.environ.get("CTX_DISABLE_SINGLE_INSTANCE") == "1":
        return False
    if os.environ.get("CTX_ALLOW_MULTIPLE_INSTANCES") == "1":
        return False
    argv0 = sys.argv[0] if sys.argv else ""
    if not argv0:
        return False
    try:
        entrypoint = Path(argv0).resolve()
    except Exception:
        return False
    if entrypoint.name != "main.py":
        return False
    app_root = entrypoint.parent
    return (app_root / "manifest.json").exists()


def enforce_single_instance_if_app() -> None:
    if not _should_enforce_single_instance():
        return
    app_root = Path(sys.argv[0]).resolve().parent
    if _acquire_instance_lock(app_root) is not None:
        return
    print(f"[INFO] {app_root.name} is already running.", file=sys.stderr)
    raise SystemExit(0)


