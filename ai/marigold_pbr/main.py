import os
import sys
from pathlib import Path


LEGACY_ID = "marigold_pbr"
LEGACY_SCOPE = "file"

APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"
REPO_ROOT = APP_ROOT.parents[1]
SHARED_ROOT = REPO_ROOT / "dev-tools" / "runtime" / "Shared"
SHARED_PACKAGE_ROOT = SHARED_ROOT / "contexthub"

os.chdir(LEGACY_ROOT)
for entry in (LEGACY_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if entry.exists():
        sys.path.insert(0, str(entry))

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)


def _capture_mode():
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"


def _pick_targets():
    if LEGACY_SCOPE in {"background", "tray_only", "standalone"}:
        return []

    if _capture_mode():
        try:
            from utils.headless_inputs import get_headless_targets
            return get_headless_targets(LEGACY_ID, LEGACY_SCOPE, LEGACY_ROOT)
        except Exception:
            return []

    return [arg for arg in sys.argv[1:] if arg]


def _show_dependency_error(message: str) -> None:
    print(message, file=sys.stderr)


def main():
    try:
        from utils.i18n import load_extra_strings

        loc_file = LEGACY_ROOT / "locales.json"
        if loc_file.exists():
            load_extra_strings(loc_file)
    except Exception:
        pass

    try:
        from features.ai.marigold_pbr_qt_app import start_app
    except ImportError as exc:
        _show_dependency_error(f"PySide6/Requirements error: {exc}")
        return

    start_app(_pick_targets())


if __name__ == "__main__":
    main()
