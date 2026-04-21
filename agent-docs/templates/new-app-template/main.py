import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime
from contexthub.utils.startup_errors import format_startup_error

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if path.exists():
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

# Replace these placeholders when generating a new app.
APP_MODULE = "features.your_domain.your_app_qt_app"
APP_ENTRYPOINT = "start_app"


def _load_app_entrypoint():
    module = __import__(APP_MODULE, fromlist=[APP_ENTRYPOINT])
    entrypoint = getattr(module, APP_ENTRYPOINT)
    return entrypoint


def main() -> int:
    try:
        start_app = _load_app_entrypoint()
        start_app([])
        return 0
    except Exception as exc:
        print(format_startup_error(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
