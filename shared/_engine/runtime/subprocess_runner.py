"""Centralised subprocess helpers used by every batch service.

This file consolidates two patterns that were duplicated across ~24
service modules:

1. The Windows `CREATE_NO_WINDOW` constant (0x08000000) to suppress
   transient console windows when invoking ffmpeg / external CLIs from a
   GUI process. Each service used to redefine this locally.

2. A cancellable Popen wrapper that registers the running process in an
   `active_processes` list, calls `communicate()`, and returns a
   normalised result dict.

Use ``CREATE_NO_WINDOW`` for any ``subprocess.run`` /
``subprocess.Popen`` invocation; on non-Windows it's 0 (no-op).
"""
from __future__ import annotations

import os
import subprocess
from typing import Iterable, Mapping, Optional, Sequence


# 0x08000000 is the value of ``subprocess.CREATE_NO_WINDOW`` on Windows
# (Python 3.7+). We define our own constant so non-Windows platforms get
# 0 (a no-op flag) without an ``if os.name == "nt"`` at every call site.
CREATE_NO_WINDOW: int = 0x08000000 if os.name == "nt" else 0


def run(
    cmd: Sequence[str],
    *,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    errors: str = "ignore",
    env: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
    cwd: Optional[str] = None,
):
    """Thin wrapper around ``subprocess.run`` that always passes
    ``creationflags=CREATE_NO_WINDOW`` on Windows so GUI apps don't flash
    a console window for every external invocation.
    """
    return subprocess.run(
        list(cmd),
        capture_output=capture_output,
        text=text,
        check=check,
        errors=errors,
        env=env,
        timeout=timeout,
        cwd=cwd,
        creationflags=CREATE_NO_WINDOW,
    )


def popen(
    cmd: Sequence[str],
    *,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[str] = None,
) -> subprocess.Popen:
    """Like :func:`run` but returns a :class:`subprocess.Popen` so the
    caller can manage cancellation / streaming themselves.
    """
    return subprocess.Popen(
        list(cmd),
        stdout=stdout,
        stderr=stderr,
        env=env,
        cwd=cwd,
        creationflags=CREATE_NO_WINDOW,
    )


def run_cancellable(
    cmd: Sequence[str],
    *,
    active_processes: list,
    cancel_predicate,
    label: str = "",
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[str] = None,
) -> dict:
    """Run ``cmd`` while honouring a cancellation flag.

    The process is appended to ``active_processes`` for the duration so a
    sibling thread can call ``.terminate()`` on it (the standard cancel
    pattern in our batch services). ``cancel_predicate`` is called once
    before launch to short-circuit if the user has already cancelled.

    Returns a dict shaped:
        {"ok": bool, "error": str | None, "returncode": int | None}
    """
    if cancel_predicate():
        return {"ok": False, "error": "Cancelled", "returncode": None}

    try:
        proc = popen(cmd, env=env, cwd=cwd)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{label}: {exc}" if label else str(exc), "returncode": None}

    active_processes.append(proc)
    try:
        _stdout, stderr_bytes = proc.communicate()
    finally:
        if proc in active_processes:
            active_processes.remove(proc)

    if proc.returncode != 0:
        msg = stderr_bytes.decode(errors="ignore") if isinstance(stderr_bytes, (bytes, bytearray)) else (stderr_bytes or "")
        prefix = f"{label}: " if label else ""
        return {"ok": False, "error": f"{prefix}{msg or 'Unknown error'}", "returncode": proc.returncode}

    return {"ok": True, "error": None, "returncode": proc.returncode}


__all__ = [
    "CREATE_NO_WINDOW",
    "run",
    "popen",
    "run_cancellable",
]
