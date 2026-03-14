"""PDF split service – UI-free business logic."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional


def split_to_pages(
    pdf_path: Path,
    output_dir: Path,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> List[Path]:
    """Split a PDF into one file per page.

    Returns:
        List of generated PDF paths.
    """
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    results: List[Path] = []

    for i, page in enumerate(reader.pages):
        if on_progress:
            on_progress(i, total, f"page {i + 1}")
        writer = PdfWriter()
        writer.add_page(page)
        out = output_dir / f"{pdf_path.stem}_page_{i + 1:03d}.pdf"
        with open(out, "wb") as f:
            writer.write(f)
        results.append(out)

    if on_progress:
        on_progress(total, total, "")
    return results


def split_to_images(
    pdf_path: Path,
    output_dir: Path,
    fmt: str = "PNG",
    dpi: int = 300,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> List[Path]:
    """Render each PDF page as an image.

    Args:
        fmt: ``"PNG"`` or ``"JPEG"``.
        dpi: Rendering resolution.

    Returns:
        List of generated image paths.
    """
    from pdf2image import convert_from_path

    images = convert_from_path(str(pdf_path), dpi=dpi)
    ext = ".png" if fmt.upper() == "PNG" else ".jpg"
    total = len(images)
    results: List[Path] = []

    for i, image in enumerate(images):
        if on_progress:
            on_progress(i, total, f"page {i + 1}")
        out = output_dir / f"{pdf_path.stem}_page_{i + 1:03d}{ext}"
        image.save(str(out), fmt.upper())
        results.append(out)

    if on_progress:
        on_progress(total, total, "")
    return results
