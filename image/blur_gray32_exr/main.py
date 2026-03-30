import os
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = APP_ROOT.parent / "_engine"
REPO_ROOT = APP_ROOT.parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for entry in (ENGINE_ROOT, SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if entry.exists():
        sys.path.insert(0, str(entry))

if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)


def _capture_mode() -> bool:
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"


def _pick_targets() -> list[Path]:
    return [Path(arg) for arg in sys.argv[1:] if arg and Path(arg).exists()]


def _prompt_radius(targets: list[Path]) -> float | None:
    from features.image.blur_gray32_exr.qt_app import BlurGray32DialogRequest, run_blur_gray32_dialog

    request = BlurGray32DialogRequest(
        app_root=APP_ROOT,
        title="Blur To Gray32 EXR",
        subtitle="Apply edge-preserving smoothing to grayscale data and save float32 EXR outputs next to the source images.",
        item_count=len(targets),
        item_label="images",
        output_rule="Creates *_blur_gray32.exr files next to each source image.",
        confirm_label="Run",
        default_radius=2.0,
    )
    result = run_blur_gray32_dialog(request)
    if result is None:
        return None
    return float(result["radius"])


def main() -> int:
    targets = _pick_targets()
    if not targets and not _capture_mode():
        return 0

    radius = _prompt_radius(targets)
    if radius is None:
        return 0
    if _capture_mode():
        return 0

    from features.image.blur_gray32_exr.console import run_blur_gray32_exr_console

    return run_blur_gray32_exr_console(targets, radius)


if __name__ == "__main__":
    raise SystemExit(main())
