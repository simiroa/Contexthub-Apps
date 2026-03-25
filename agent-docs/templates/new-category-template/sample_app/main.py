import os
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

LEGACY_ROOT = APP_ROOT.parent / "_engine"
SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (LEGACY_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if path.exists():
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)


def main():
    print("Replace sample_app with a real app entry point:", APP_ROOT)


if __name__ == "__main__":
    main()
