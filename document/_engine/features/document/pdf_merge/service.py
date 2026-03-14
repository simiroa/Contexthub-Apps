"""PDF merge service – UI-free business logic."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional


def merge_pdfs(
    files: List[Path],
    dest: Path,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> Path:
    """Merge *files* into a single PDF at *dest*.

    Args:
        files: Ordered list of PDF paths to merge.
        dest: Output file path.
        on_progress: ``(current_idx, total, filename)`` callback.

    Returns:
        The destination path on success.

    Raises:
        ImportError: If ``pypdf`` is not installed.
        RuntimeError: On merge failure.
    """
    from pypdf import PdfWriter

    writer = PdfWriter()
    total = len(files)

    for idx, pdf in enumerate(files):
        if on_progress:
            on_progress(idx, total, pdf.name)
        writer.append(str(pdf))

    dest.parent.mkdir(parents=True, exist_ok=True)
    writer.write(str(dest))
    writer.close()

    if on_progress:
        on_progress(total, total, "")

    return dest
