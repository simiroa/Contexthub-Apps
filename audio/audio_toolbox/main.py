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


def _load_locales() -> None:
    try:
        from utils.i18n import load_extra_strings

        loc_file = ENGINE_ROOT / "locales.json"
        if loc_file.exists():
            load_extra_strings(loc_file)
    except Exception:
        pass


def main() -> int:
    _load_locales()
    targets = _pick_targets()
    if not targets and _capture_mode():
        targets = [ENGINE_ROOT / "manuals" / "headless_inputs" / "sample.wav"]

    from features.audio.audio_toolbox_qt_app import start_app

    return start_app(targets, APP_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
