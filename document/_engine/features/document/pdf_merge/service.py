"""PDF merge service and UI helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, List, Optional

from .state import PdfMergeState


def merge_pdfs(
    files: List[Path],
    dest: Path,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> Path:
    """Merge *files* into a single PDF at *dest*."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    total = len(files)

    for idx, pdf in enumerate(files):
        if on_progress:
            on_progress(idx, total, pdf.name)
        writer.append(str(pdf))

    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as handle:
        writer.write(handle)
    writer.close()

    if on_progress:
        on_progress(total, total, "")

    return dest


class PdfMergeService:
    def __init__(self) -> None:
        self.state = PdfMergeState()

    def add_inputs(self, paths: List[str]) -> None:
        for raw in paths:
            path = Path(raw)
            if not path.exists() or path.suffix.lower() != ".pdf":
                continue
            if path in self.state.files:
                continue
            self.state.files.append(path)
        if self.state.files and self.state.selected_index < 0:
            self.state.selected_index = 0
        self._sync_status()

    def remove_selected(self) -> None:
        index = self.state.selected_index
        if 0 <= index < len(self.state.files):
            self.state.files.pop(index)
        if not self.state.files:
            self.state.selected_index = -1
        else:
            self.state.selected_index = min(index, len(self.state.files) - 1)
        self._sync_status()

    def clear_inputs(self) -> None:
        self.state.files.clear()
        self.state.selected_index = -1
        self.state.detail_text = ""
        self._sync_status()

    def set_selected_index(self, index: int) -> None:
        if 0 <= index < len(self.state.files):
            self.state.selected_index = index
        elif not self.state.files:
            self.state.selected_index = -1
        self._sync_status()

    def move_selected_up(self) -> bool:
        index = self.state.selected_index
        if index <= 0 or index >= len(self.state.files):
            return False
        self.state.files[index - 1], self.state.files[index] = self.state.files[index], self.state.files[index - 1]
        self.state.selected_index = index - 1
        self._sync_status()
        return True

    def move_selected_down(self) -> bool:
        index = self.state.selected_index
        if index < 0 or index >= len(self.state.files) - 1:
            return False
        self.state.files[index + 1], self.state.files[index] = self.state.files[index], self.state.files[index + 1]
        self.state.selected_index = index + 1
        self._sync_status()
        return True

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir).expanduser()
        self.state.output_options.file_prefix = file_prefix.strip() or "merged"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def selected_file(self) -> Optional[Path]:
        index = self.state.selected_index
        if 0 <= index < len(self.state.files):
            return self.state.files[index]
        return None

    def build_output_path(self) -> Path:
        base_dir = self.state.output_options.output_dir
        prefix = self.state.output_options.file_prefix.strip() or "merged"
        path = base_dir / f"{prefix}.pdf"
        counter = 2
        while path.exists():
            path = base_dir / f"{prefix}_{counter}.pdf"
            counter += 1
        return path

    def run_merge(self, on_progress: Optional[Callable[[int, int, str], None]] = None) -> Path:
        if len(self.state.files) < 2:
            raise ValueError("Select at least two PDF files.")
        dest = self.build_output_path()
        self.state.is_processing = True
        self.state.error = ""
        self.state.progress = 0.0
        self.state.status_text = "Merging PDFs..."
        self.state.detail_text = ""

        def _wrapped(current: int, total: int, name: str) -> None:
            self.state.progress = (current / total) if total else 0.0
            self.state.detail_text = name
            if on_progress is not None:
                on_progress(current, total, name)

        try:
            output = merge_pdfs(self.state.files, dest, _wrapped)
        except Exception as exc:
            self.state.is_processing = False
            self.state.error = str(exc)
            self.state.status_text = "Merge failed"
            raise

        self.state.is_processing = False
        self.state.progress = 1.0
        self.state.status_text = "Merge complete"
        self.state.detail_text = output.name
        self.state.last_output_path = output
        return output

    def reveal_output_dir(self) -> None:
        path = self.state.output_options.output_dir
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)

    def _sync_status(self) -> None:
        count = len(self.state.files)
        if count == 0:
            self.state.status_text = "Ready"
            self.state.detail_text = "Add PDF files to merge."
            return
        selected = self.selected_file()
        self.state.status_text = f"{count} PDF{'s' if count != 1 else ''} queued"
        self.state.detail_text = str(selected) if selected else ""
