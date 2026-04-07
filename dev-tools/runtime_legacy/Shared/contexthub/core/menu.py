import os
import subprocess
import sys
import shutil
from pathlib import Path
from tkinter import messagebox

try:
    from .manifest_index import scan_manifests
    from .settings import load_settings
except ImportError:
    # Allow direct script execution (not as a package)
    _core_dir = Path(__file__).resolve().parent
    _pkg_root = _core_dir.parent
    sys.path.insert(0, str(_pkg_root))
    from core.manifest_index import scan_manifests
    from core.settings import load_settings


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "Apps_installed").exists():
            return parent
    return current.parents[4]


def _log_launch(message: str) -> None:
    try:
        root = _repo_root()
        log_dir = root / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "context_menu_launch.log"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass


def _show_ai_conda_warning(reason: str) -> None:
    if os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1":
        return
    if os.environ.get("CTX_AI_CONDA_WARNED") == "1":
        return
    os.environ["CTX_AI_CONDA_WARNED"] = "1"
    try:
        messagebox.showwarning(
            "AI Conda Recommended",
            "AI tools prefer a Conda environment.\n\n"
            "Install Conda and create/configure the AI environment to use the recommended setup.\n\n"
            f"Reason: {reason}\n\n"
            "Falling back to the current Python environment for now.",
        )
    except Exception:
        pass


def _find_conda_exe(settings: dict) -> Path | None:
    candidates = [
        settings.get("AI_CONDA_EXE"),
        os.environ.get("CTX_AI_CONDA_EXE"),
        os.environ.get("CONDA_EXE"),
        shutil.which("conda"),
        shutil.which("conda.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def _resolve_conda_python(settings: dict) -> tuple[Path | None, str | None]:
    env_path = settings.get("AI_CONDA_ENV_PATH") or os.environ.get("CTX_AI_CONDA_ENV_PATH")
    if env_path:
        candidate = Path(env_path) / "python.exe"
        if candidate.exists():
            return candidate, None
        return None, f"Configured Conda env path not found: {env_path}"

    conda_exe = _find_conda_exe(settings)
    if not conda_exe:
        return None, "Conda executable was not found"

    env_name = settings.get("AI_CONDA_ENV_NAME") or os.environ.get("CTX_AI_CONDA_ENV_NAME") or "contexthub-ai"
    try:
        result = subprocess.run(
            [str(conda_exe), "info", "--base"],
            capture_output=True,
            text=True,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        base_path = Path((result.stdout or "").strip())
        if base_path.exists():
            candidate = base_path / "envs" / env_name / "python.exe"
            if candidate.exists():
                return candidate, None
    except Exception as exc:
        return None, f"Failed to inspect Conda base: {exc}"

    return None, f"Conda env '{env_name}' was not found"


def _resolve_python(category: str) -> Path:
    root = _repo_root()
    settings = load_settings()

    if category == "ai" and settings.get("AI_ENV_MODE", "prefer_conda") != "disabled":
        conda_python, reason = _resolve_conda_python(settings)
        if conda_python:
            return conda_python
        if reason:
            _show_ai_conda_warning(reason)

    candidate = root / "Runtimes" / "Envs" / category / "Scripts" / "python.exe"
    if candidate.exists():
        return candidate

    python_path = settings.get("PYTHON_PATH")
    if python_path and Path(python_path).exists():
        return Path(python_path)

    return Path(sys.executable)


def _resolve_pythonw(python_exe: Path) -> Path:
    if python_exe.name.lower() == "python.exe":
        pythonw = python_exe.parent / "pythonw.exe"
        if pythonw.exists():
            return pythonw
    return python_exe


def _launch_app(entry, targets: list[str]) -> None:
    python_exe = _resolve_python(entry.category)
    python_bin = _resolve_pythonw(python_exe) if entry.mode == "gui" else python_exe
    script_path = entry.app_dir / entry.entry_point
    args = [str(python_bin), str(script_path)]
    if targets:
        args.extend(targets)

    creation_flags = 0x08000000 if entry.mode == "gui" else 0
    env = os.environ.copy()
    env.setdefault("CTX_APP_ROOT", str(entry.app_dir.parent))
    _log_launch(
        f"launch app_id={entry.app_id} category={entry.category} "
        f"mode={entry.mode} python={python_bin} script={script_path} "
        f"targets={targets}"
    )

    subprocess.Popen(args, cwd=str(entry.app_dir), env=env, creationflags=creation_flags)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: menu.py <app_id> [target_path...]")
        return 1

    app_id = sys.argv[1]
    # Collect all remaining arguments as target paths
    targets = sys.argv[2:] if len(sys.argv) > 2 else []

    root = _repo_root()
    manifests = scan_manifests(root)
    entry = manifests.get(app_id)
    if not entry:
        print(f"App not found: {app_id}")
        return 1

    _launch_app(entry, targets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
