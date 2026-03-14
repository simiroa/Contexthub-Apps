"""Document conversion service – UI-free business logic.

Wraps the existing ``core.converter.DocumentConverter`` and
the ``CONVERSIONS`` format matrix from the legacy GUI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from utils.i18n import t
from features.document.core.converter import DocumentConverter


# ── format matrix (same as convert_gui.py) ───────────────────────────

CONVERSIONS: Dict[str, Dict[str, str]] = {
    ".pdf": {
        t("doc_convert.fmt_docx", "Word (DOCX)"): ".docx",
        t("doc_convert.fmt_xlsx", "Excel (XLSX)"): ".xlsx",
        t("doc_convert.fmt_pptx", "PowerPoint (PPTX)"): ".pptx",
        t("doc_convert.fmt_png", "Image (PNG)"): ".png",
        t("doc_convert.fmt_jpg", "Image (JPG)"): ".jpg",
        t("doc_convert.fmt_epub", "EPUB (E-Book)"): ".epub",
        t("doc_convert.fmt_html", "HTML (Styled)"): ".html",
        t("doc_convert.fmt_md", "Markdown (MD)"): ".md",
        t("doc_convert.fmt_images", "Extract Embedded Images"): ".images",
    },
    ".docx": {
        t("doc_convert.fmt_pdf", "PDF Document"): ".pdf",
        t("doc_convert.fmt_images", "Extract Embedded Images"): ".images",
    },
    ".doc": {t("doc_convert.fmt_pdf", "PDF Document"): ".pdf"},
    ".xlsx": {
        t("doc_convert.fmt_pdf", "PDF Document"): ".pdf",
        t("doc_convert.fmt_images", "Extract Embedded Images"): ".images",
    },
    ".xls": {t("doc_convert.fmt_pdf", "PDF Document"): ".pdf"},
    ".pptx": {
        t("doc_convert.fmt_pdf", "PDF Document"): ".pdf",
        t("doc_convert.fmt_images", "Extract Embedded Images"): ".images",
    },
    ".ppt": {t("doc_convert.fmt_pdf", "PDF Document"): ".pdf"},
    ".png": {t("doc_convert.fmt_pdf", "PDF Document"): ".pdf"},
    ".jpg": {t("doc_convert.fmt_pdf", "PDF Document"): ".pdf"},
    ".jpeg": {t("doc_convert.fmt_pdf", "PDF Document"): ".pdf"},
    ".md": {
        t("doc_convert.fmt_pdf", "PDF Document"): ".pdf",
        t("doc_convert.fmt_html_web", "HTML Webpage"): ".html",
    },
}


def get_common_formats(files: List[Path]) -> List[str]:
    """Return format labels supported by *all* files in the list."""
    common: Optional[Set[str]] = None
    for f in files:
        ext = f.suffix.lower()
        labels = set(CONVERSIONS.get(ext, {}).keys())
        common = labels if common is None else common & labels
    return sorted(common) if common else []


def convert_files(
    files: List[Path],
    target_label: str,
    use_subfolder: bool = True,
    options: Optional[dict] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[int, List[str]]:
    """Convert *files* using the given format label.

    Returns:
        ``(success_count, error_messages)``
    """
    options = options or {}
    converter = DocumentConverter()
    success = 0
    errors: List[str] = []
    total = len(files)

    for idx, fpath in enumerate(files):
        if on_progress:
            on_progress(idx, total, fpath.name)

        try:
            ext = fpath.suffix.lower()
            target_ext = CONVERSIONS.get(ext, {}).get(target_label)
            if not target_ext:
                raise ValueError(f"No target for {ext} → {target_label}")

            out_dir = fpath.parent
            if use_subfolder:
                out_dir = out_dir / "Converted_Docs"
                out_dir.mkdir(exist_ok=True)

            converter.convert(fpath, target_ext, out_dir, options)
            success += 1
        except Exception as exc:
            errors.append(f"{fpath.name}: {exc}")

    if on_progress:
        on_progress(total, total, "")

    return success, errors
