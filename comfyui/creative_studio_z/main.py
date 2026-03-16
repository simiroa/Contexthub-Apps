import os
import sys
from pathlib import Path


LEGACY_ID = "creative_studio_z"
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
        from features.comfyui.creative_studio_z_qt_app import start_app
    except ImportError as exc:
        _show_dependency_error(f"PySide6 is required to run this app.\n\n{exc}")
        return

    start_app([])


if __name__ == "__main__":
    main()
