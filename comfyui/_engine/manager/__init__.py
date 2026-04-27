import os
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = APP_ROOT.parent
COMFYUI_ROOT = ENGINE_ROOT.parent
REPO_ROOT = APP_ROOT.parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime
from contexthub.utils.startup_errors import format_startup_error

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (ENGINE_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if path.exists():
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

if str(APP_ROOT) in sys.path:
    sys.path.remove(str(APP_ROOT))

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(COMFYUI_ROOT)


def _set_high_dpi_awareness() -> None:
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> int:
    try:
        _set_high_dpi_awareness()

        from core.logger import setup_logger

        setup_logger(file_prefix="app")

        from manager.ui.app import ContextUpManager

        app = ContextUpManager(COMFYUI_ROOT)
        app.mainloop()
        return 0
    except Exception as exc:
        import traceback

        error_msg = f"Manager Startup Fatal Error: {format_startup_error(exc)}\n{traceback.format_exc()}"
        print(error_msg)

        try:
            log_path = COMFYUI_ROOT / "logs" / "manager_crash.log"
            log_path.parent.mkdir(exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                import datetime

                f.write(f"\n[{datetime.datetime.now()}] {error_msg}\n")
        except Exception:
            pass

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
