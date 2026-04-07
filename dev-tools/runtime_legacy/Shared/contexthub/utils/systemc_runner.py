import os
import subprocess
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000


def _resolve_exe(app_id: str, app_root: Path) -> Path | None:
    candidates = [
        app_root / f"{app_id}.exe",
        app_root / "app.exe",
        app_root / "tool.exe",
    ]
    for exe in candidates:
        if exe.exists():
            return exe
    return None


def run_systemc(app_id: str, app_root: Path, targets: list[str] | None) -> bool:
    exe = _resolve_exe(app_id, app_root)
    if not exe:
        return False

    args = [str(exe)]
    if targets:
        args.extend([str(t) for t in targets])

    env = os.environ.copy()
    env.setdefault("CTX_APP_ID", app_id)
    env.setdefault("CTX_APP_ROOT", str(app_root))

    subprocess.Popen(args, cwd=str(app_root), env=env, creationflags=CREATE_NO_WINDOW)
    return True
