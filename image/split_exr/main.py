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
        sys.path.insert(0, str(entry))

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)


def _capture_mode() -> bool:
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"


def _pick_targets() -> list[Path]:
    return [Path(arg) for arg in sys.argv[1:] if arg and Path(arg).exists()]


def _show_confirm(targets: list[Path]) -> bool:
    from contexthub.ui.qt.confirm_dialog import ConfirmRequest, run_confirm_dialog

    request = ConfirmRequest(
        app_root=APP_ROOT,
        title="Split EXR",
        subtitle="Confirm the selected EXR files, then continue in a console progress flow.",
        item_count=len(targets),
        item_label="files",
        output_rule="Creates a <name>_split folder and writes PNG layers by default.",
        confirm_label="Split",
    )
    return run_confirm_dialog(request) is not None


def main() -> int:
    targets = _pick_targets()
    if not targets and not _capture_mode():
        return 0
    if not _show_confirm(targets):
        return 0
    if _capture_mode():
        return 0

    from features.image.split_exr_console import run_split_exr_console

    return run_split_exr_console(targets, output_format="png")


if __name__ == "__main__":
    raise SystemExit(main())
