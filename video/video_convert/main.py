import os
import sys
import time
from pathlib import Path

_T0 = time.perf_counter()


def _log_startup(label: str) -> None:
    if os.environ.get("CTX_STARTUP_TRACE"):
        print(f"[startup] {label} t+{(time.perf_counter() - _T0) * 1000:.0f}ms", file=sys.stderr)


APP_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = APP_ROOT.parent / "_engine"
REPO_ROOT = APP_ROOT.parents[1]

# 1. Inject repo root so we can load runtime_bootstrap
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 2. Setup shared runtime properties
from runtime_bootstrap import resolve_shared_runtime, enforce_single_instance_if_app
from contexthub.utils.startup_errors import format_startup_error
SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)

# 3. Build path list in priority order (local engine > shared engine > shared runtime)
SHARED_ENGINE_ROOT = REPO_ROOT / "shared" / "_engine"
for entry in (REPO_ROOT, ENGINE_ROOT, SHARED_ENGINE_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if entry.exists():
        sys.path.insert(0, str(entry))

# 4. Enforce single instance logic explicitly
enforce_single_instance_if_app()


def main() -> None:
    _log_startup("entering main")
    try:
        from features.video.video_convert_qt_app import start_app
    except ImportError as exc:
        print(format_startup_error(exc), file=sys.stderr)
        return
    _log_startup("qt_app imported")

    # Pass remaining args as targets
    start_app([Path(arg) for arg in sys.argv[1:] if arg and Path(arg).exists()], APP_ROOT)

if __name__ == "__main__":
    main()
