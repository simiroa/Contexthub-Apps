import os
import sys
from pathlib import Path

LEGACY_ID = 'auto_lod'
LEGACY_SCOPE = 'file'

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from runtime_bootstrap import resolve_shared_runtime
LEGACY_ROOT = APP_ROOT.parent / "_engine"
os.chdir(LEGACY_ROOT)
sys.path.insert(0, str(LEGACY_ROOT))

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)

# Ensure Shared runtime is in path for i18n and Flet tokens
SHARED_PATH, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (SHARED_PATH, SHARED_PACKAGE_ROOT):
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)

try:
    from utils.i18n import load_extra_strings
    load_extra_strings(LEGACY_ROOT / "locales.json")
except Exception:
    pass

def _capture_mode():
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"

def _pick_targets():
    if _capture_mode():
        return []
    
    args = [a for a in sys.argv[1:] if Path(a).exists()]
    if args:
        return args
    return []

def _run_flet(targets):
    from features.mesh.mesh_flet import start_app
    # mode='lod' for auto_lod
    start_app(targets, mode='lod')

def main():
    targets = _pick_targets()
    _run_flet(targets)

if __name__ == "__main__":
    main()
