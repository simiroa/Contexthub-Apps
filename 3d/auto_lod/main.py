import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = APP_ROOT.parent / "_engine"
REPO_ROOT = APP_ROOT.parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for entry in (ENGINE_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if entry.exists():
        path_str = str(entry)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)


def _pick_targets() -> list[str]:
    return [arg for arg in sys.argv[1:] if arg and Path(arg).exists()]


def _load_locales() -> None:
    try:
        from features.mesh.mesh_qt_shared import load_mesh_locales

        load_mesh_locales(ENGINE_ROOT)
    except Exception:
        pass


def _show_dependency_error(message: str) -> None:
    print(message, file=sys.stderr)


def _run_qt(targets: list[str]) -> int:
    try:
        from features.mesh.auto_lod_qt_app import start_app
    except ImportError as exc:
        _show_dependency_error(f"PySide6 is required to run this app.\n\n{exc}")
        return 1
    return start_app(APP_ROOT, targets)


def main() -> int:
    _load_locales()
    return _run_qt(_pick_targets())


if __name__ == "__main__":
    raise SystemExit(main())
