import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"
ROOT = Path(__file__).resolve().parents[2]
SHARED_ROOT = ROOT / "dev-tools" / "runtime" / "Shared"
SHARED_PACKAGE_ROOT = SHARED_ROOT / "contexthub"

os.chdir(LEGACY_ROOT)
for path in (LEGACY_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)
os.environ.setdefault("CTX_APP_ROOT", str(APP_ROOT))


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    from features.ai.standalone.qwen3_tts_flet_app import open_qwen3_tts_flet

    open_qwen3_tts_flet(target)


if __name__ == "__main__":
    main()
