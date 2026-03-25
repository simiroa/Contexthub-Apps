"""Document conversion service for the Qt document conversion UI."""

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


class DocConvertService:
    def __init__(self):
        self.converter = DocumentConverter()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        self.converter.cancel()

    def convert_files(
        self,
        files: List[Path],
        target_label: str,
        *,
        use_subfolder: bool = False,
        custom_output_dir: Optional[Path] = None,
        options: Optional[dict] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> tuple[int, List[str], Optional[Path]]:
        options = options or {}
        self._cancelled = False
        success = 0
        errors: List[str] = []
        total = len(files)
        last_output_dir: Optional[Path] = None

        for idx, fpath in enumerate(files):
            if self._cancelled:
                errors.append("Conversion cancelled by user.")
                break

            if on_progress:
                on_progress(idx + 1, total, fpath.name)

            try:
                ext = fpath.suffix.lower()
                target_ext = CONVERSIONS.get(ext, {}).get(target_label)
                if not target_ext:
                    raise ValueError(f"No target for {ext} -> {target_label}")

                out_dir = custom_output_dir or fpath.parent
                if use_subfolder and custom_output_dir is None:
                    out_dir = out_dir / "Converted_Docs"
                out_dir.mkdir(parents=True, exist_ok=True)

                self.converter.convert(fpath, target_ext, out_dir, options)
                last_output_dir = out_dir
                success += 1
            except Exception as exc:
                errors.append(f"{fpath.name}: {exc}")

        if on_progress and not self._cancelled:
            on_progress(total, total, "")

        return success, errors, last_output_dir


def convert_files(
    files: List[Path],
    target_label: str,
    use_subfolder: bool = True,
    custom_output_dir: Optional[Path] = None,
    options: Optional[dict] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[int, List[str]]:
    """Convert *files* using the given format label.

    Returns:
        ``(success_count, error_messages)``
    """
    service = DocConvertService()
    success, errors, _ = service.convert_files(
        files,
        target_label,
        use_subfolder=use_subfolder,
        custom_output_dir=custom_output_dir,
        options=options,
        on_progress=on_progress,
    )
    return success, errors
