import os
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = APP_ROOT.parent / "_engine"
REPO_ROOT = APP_ROOT.parents[1]

# 1. Inject repo root so we can load runtime_bootstrap
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 2. Setup shared runtime properties
from runtime_bootstrap import resolve_shared_runtime, enforce_single_instance_if_app
SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)

# 3. Build path list in priority order (local engine > shared engine > shared runtime)
SHARED_ENGINE_ROOT = REPO_ROOT / "shared" / "_engine"
for entry in (REPO_ROOT, ENGINE_ROOT, SHARED_ENGINE_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if entry.exists():
        sys.path.insert(0, str(entry))

# 4. Enforce single instance logic explicitly
enforce_single_instance_if_app()


def main() -> None:
    try:
        from features.image.simple_normal_roughness_qt_app import start_app
    except ImportError as exc:
        print(f"Failed to load UI components: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return

    # Pass remaining args as targets
    start_app([Path(arg) for arg in sys.argv[1:] if arg and Path(arg).exists()], APP_ROOT)

if __name__ == "__main__":
    main()
