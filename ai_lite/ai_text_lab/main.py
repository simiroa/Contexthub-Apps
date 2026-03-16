import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent

def _setup_paths():
    REPO_ROOT = APP_ROOT.resolve().parents[1]
    _engine_root = APP_ROOT.parent / "_engine"
    
    # Add REPO_ROOT for runtime_bootstrap
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    
    from runtime_bootstrap import resolve_shared_runtime
    SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
    
    # Feature specific path (service/state)
    feature_dir = _engine_root / "features" / "tools"
    
    # Critical Paths for App/Shared
    # We insert SHARED_PACKAGE_ROOT first so 'core', 'utils' can be found as top-level
    new_paths = [
        str(feature_dir),
        str(_engine_root),
        str(SHARED_PACKAGE_ROOT),
        str(SHARED_ROOT),
    ]
    
    for p in new_paths:
        if os.path.exists(p) and p not in sys.path:
            sys.path.insert(0, p)
            
    os.environ.setdefault("CTX_APP_ROOT", str(APP_ROOT))

def main():
    _setup_paths()
    # Now import app components
    try:
        from ai_text_lab_qt_app import start_app
        sys.exit(start_app())
    except Exception as e:
        print(f"Failed to start AI Text Lab: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
