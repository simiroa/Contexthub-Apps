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


def _capture_mode() -> bool:
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"


def _pick_targets() -> list[Path]:
    return [Path(arg) for arg in sys.argv[1:] if arg and Path(arg).exists()]


def _load_locales() -> None:
    try:
        from features.mesh.mesh_qt_shared import load_mesh_locales

        load_mesh_locales(ENGINE_ROOT)
    except Exception:
        pass


def _show_confirm(targets: list[Path]) -> bool:
    from contexthub.ui.qt.confirm_dialog import ConfirmRequest, run_confirm_dialog

    request = ConfirmRequest(
        app_root=APP_ROOT,
        title="Open with Mayo",
        subtitle="Confirm the selected 3D files, then open them in Mayo.",
        item_count=len(targets),
        item_label="files",
        output_rule="Launches the selected files in the Mayo viewer.",
        confirm_label="Open",
    )
    return run_confirm_dialog(request) is not None


def main() -> int:
    _load_locales()
    targets = _pick_targets()
    if not targets and not _capture_mode():
        return 0
    if not _show_confirm(targets):
        return 0
    if _capture_mode():
        return 0

    from features.mesh.mesh_console import run_open_with_mayo_console

    return run_open_with_mayo_console(targets)


if __name__ == "__main__":
    raise SystemExit(main())
