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


def _show_confirm(targets: list[Path]) -> str | None:
    from contexthub.ui.qt.confirm_dialog import ConfirmChoice, ConfirmRequest, run_confirm_dialog

    request = ConfirmRequest(
        app_root=APP_ROOT,
        title="PDF Split",
        subtitle="Confirm the selected PDFs, then continue in a console progress flow.",
        item_count=len(targets),
        item_label="pdfs",
        output_rule="Creates a <name>_split folder next to each source document.",
        option_label="Output Format",
        option_choices=(
            ConfirmChoice("pdf", "PDF"),
            ConfirmChoice("png", "PNG"),
            ConfirmChoice("jpeg", "JPEG"),
        ),
        option_value="pdf",
        confirm_label="Split",
    )
    result = run_confirm_dialog(request)
    if result is None:
        return None
    return result.get("option") or "pdf"


def main() -> int:
    targets = _pick_targets()
    if not targets and not _capture_mode():
        return 0
    selected_format = _show_confirm(targets)
    if selected_format is None:
        return 0
    if _capture_mode():
        return 0

    from features.document.pdf_split_console import run_pdf_split_console

    return run_pdf_split_console(targets, output_format=selected_format)


if __name__ == "__main__":
    raise SystemExit(main())
