import os
import sys
from pathlib import Path


APP_ID = "subtitle_qc"
APP_SCOPE = "file"
APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.resolve().parents[1]
ENGINE_ROOT = APP_ROOT.parent / "_engine"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
os.chdir(ENGINE_ROOT)
for path in (REPO_ROOT, ENGINE_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)


def _capture_mode() -> bool:
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"


def _pick_targets() -> list[Path]:
    if APP_SCOPE in {"background", "tray_only", "standalone"}:
        return []

    if _capture_mode():
        try:
            from utils.headless_inputs import get_headless_targets

            return [Path(path) for path in get_headless_targets(APP_ID, APP_SCOPE, ENGINE_ROOT)]
        except Exception:
            return []

    return [Path(arg) for arg in sys.argv[1:] if arg and Path(arg).exists()]


def _show_dependency_error(message: str) -> None:
    print(message, file=sys.stderr)


def _load_localized_strings() -> None:
    try:
        from utils.i18n import load_extra_strings

        locale_file = ENGINE_ROOT / "locales.json"
        if locale_file.exists():
            load_extra_strings(locale_file)
    except Exception:
        pass


def main() -> None:
    _load_localized_strings()
    try:
        from features.ai.subtitle_qc_qt_app import start_app
    except Exception as exc:
        _show_dependency_error(f"PySide6 is required to run this app.\n\n{exc}")
        return

    start_app(_pick_targets(), APP_ROOT)


if __name__ == "__main__":
    main()
