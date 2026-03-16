import os
import sys
from pathlib import Path


APP_ID = "remove_audio"
APP_TITLE = "Remove Audio"
APP_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = APP_ROOT.parent / "_engine"
REPO_ROOT = APP_ROOT.parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)

for entry in (REPO_ROOT, ENGINE_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
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
        title="Remove Audio",
        subtitle="Confirm the selected videos, then continue in a console progress flow.",
        item_count=len(targets),
        item_label="videos",
        output_rule="Creates *_mute files next to each source video.",
        confirm_label="Remove",
    )
    return run_confirm_dialog(request) is not None


def main() -> int:
    try:
        from utils.i18n import load_extra_strings

        loc_file = ENGINE_ROOT / "locales.json"
        if loc_file.exists():
            load_extra_strings(loc_file)
    except Exception:
        pass

    targets = _pick_targets()
    if not targets and not _capture_mode():
        return 0
    if not _show_confirm(targets):
        return 0
    if _capture_mode():
        return 0

    from features.video.remove_audio_console import run_remove_audio_console

    return run_remove_audio_console(targets, APP_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
