from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any, List, Optional

from utils.i18n import t
from features.document.core.converter import DocumentConverter
from features.document.doc_convert_state import DocConvertState, InputAsset

# ── format matrix (same as service.py) ───────────────────────────

CONVERSIONS: dict[str, dict[str, str]] = {
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
    common: Optional[set[str]] = None
    for f in files:
        ext = f.suffix.lower()
        labels = set(CONVERSIONS.get(ext, {}).keys())
        common = labels if common is None else common & labels
    return sorted(common) if common else []


class DocConvertService:
    def __init__(self) -> None:
        self.state = DocConvertState()
        self.converter = DocumentConverter()
        self._cancelled = False
        self._workflow_names = ["Default"]

    def get_workflow_names(self) -> list[str]:
        return list(self._workflow_names)

    def select_workflow(self, name: str) -> None:
        self.state.workflow_name = name
        self.state.workflow_description = "Convert documents based on their formats."

    def get_ui_definition(self) -> list[dict[str, Any]]:
        # Dynamic UI definition based on input files
        files = [asset.path for asset in self.state.input_assets]
        formats = get_common_formats(files)
        
        ui_def = [
            {
                "key": "target_format",
                "label": t("doc_convert.target_format", "Target Format"),
                "type": "choice",
                "options": formats,
                "default": formats[0] if formats else ""
            }
        ]
        
        # Add DPI if image conversion is involved
        current_format = self.state.parameter_values.get("target_format", "")
        if "Image" in str(current_format) or "이미지" in str(current_format):
            ui_def.append({
                "key": "dpi",
                "label": "DPI",
                "type": "choice",
                "options": ["72", "150", "200", "300", "400", "600"],
                "default": "300"
            })
            
        return ui_def

    def add_inputs(self, paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            if any(asset.path == path for asset in self.state.input_assets):
                continue
            self.state.input_assets.append(InputAsset(path=path, kind="file"))
        
        if self.state.input_assets and self.state.preview_path is None:
            self.state.preview_path = self.state.input_assets[0].path
            
        # Update available formats in parameter values if not set
        files = [asset.path for asset in self.state.input_assets]
        formats = get_common_formats(files)
        if formats and not self.state.parameter_values.get("target_format"):
            self.state.parameter_values["target_format"] = formats[0]

    def remove_input_at(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            removed = self.state.input_assets.pop(index)
            if self.state.preview_path == removed.path:
                self.state.preview_path = self.state.input_assets[0].path if self.state.input_assets else None

    def clear_inputs(self) -> None:
        self.state.input_assets.clear()
        self.state.preview_path = None

    def set_preview_from_index(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            self.state.preview_path = self.state.input_assets[index].path

    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir)
        self.state.output_options.file_prefix = file_prefix.strip() or "doc_convert"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def reveal_output_dir(self) -> None:
        path = self.state.output_options.output_dir
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)

    def cancel(self):
        self._cancelled = True
        self.converter.cancel()

    def run_workflow(self) -> tuple[bool, str, Path | None]:
        files = [asset.path for asset in self.state.input_assets]
        target_label = str(self.state.parameter_values.get("target_format", ""))
        
        if not files:
            return False, "No input files selected.", None
        if not target_label:
            return False, "No target format selected.", None

        self.state.is_processing = True
        self.state.errors = []
        self.state.progress = 0.0
        self._cancelled = False
        
        options = {
            "dpi": int(self.state.parameter_values.get("dpi", 300)),
            "separate_pages": True
        }
        
        def on_progress(idx, total, name):
            self.state.progress = idx / total if total else 0
            self.state.status_text = f"Processing {idx}/{total}"
            self.state.detail_text = name

        success, errors, last_dir = self.converter_loop(
            files, 
            target_label, 
            options, 
            on_progress
        )

        self.state.is_processing = False
        self.state.errors = errors
        self.state.last_converted = last_dir
        self.state.progress = 1.0

        if errors:
            return True, f"Completed with {len(errors)} errors.", last_dir
        return True, f"Successfully converted {success} files.", last_dir

    def converter_loop(self, files, target_label, options, on_progress):
        success = 0
        errors = []
        total = len(files)
        last_dir = None
        
        for idx, fpath in enumerate(files):
            if self._cancelled:
                errors.append("Cancelled.")
                break
            
            if on_progress:
                on_progress(idx + 1, total, fpath.name)
                
            try:
                ext = fpath.suffix.lower()
                target_ext = CONVERSIONS.get(ext, {}).get(target_label)
                if not target_ext:
                    raise ValueError(f"No target for {ext} -> {target_label}")
                
                out_dir = self.state.output_options.output_dir
                if self.state.output_options.use_subfolder:
                    out_dir = out_dir / "Converted_Docs"
                out_dir.mkdir(parents=True, exist_ok=True)
                
                self.converter.convert(fpath, target_ext, out_dir, options)
                last_dir = out_dir
                success += 1
            except Exception as e:
                errors.append(f"{fpath.name}: {e}")
                
        return success, errors, last_dir
