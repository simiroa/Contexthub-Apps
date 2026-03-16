"""PDF Split Flet UI.

Centralized layout based on image-category patterns.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.layout import (
    action_bar,
    apply_button_sizing,
    compact_meta_strip,
    integrated_title_bar,
    section_card,
    status_badge,
)
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.window import reveal_desktop_window
from utils.i18n import t

from .service import split_to_images, split_to_pages
from .state import PdfSplitState


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if not value or value == key else value


def _file_row(path: Path) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.PICTURE_AS_PDF, size=16, color=COLORS["text_muted"]),
                ft.Text(path.name, size=11, color=COLORS["text"], expand=True, no_wrap=True),
                ft.Text("PDF", size=10, color=COLORS["text_soft"]),
            ],
            spacing=SPACING["sm"],
        ),
    )


class PdfSplitFletApp:
    def __init__(self, initial_files: List[str]):
        self.state = PdfSplitState(
            files=[Path(f) for f in initial_files if Path(f).exists() and Path(f).suffix.lower() == ".pdf"]
        )
        self.capture_mode = False

    async def main(self, page: ft.Page):
        self.page = page
        title = _tr("pdf_split.title", "PDF Split")
        configure_page(page, title, window_profile="table_heavy")
        page.bgcolor = COLORS["app_bg"]
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"

        if not self.capture_mode:
            self.file_picker = ft.FilePicker(on_result=self.on_file_result)
            page.overlay.append(self.file_picker)
        else:
            self.file_picker = None

        # controls
        self.file_list = ft.ListView(spacing=SPACING["xs"], auto_scroll=False)
        self.queue_badge = status_badge(f"{len(self.state.files)} files", "muted")
        self.mode_badge = status_badge("PDF", "accent")
        self.output_badge = status_badge("Output folder", "muted")
        self.output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        self.status_text = ft.Text(_tr("common.ready", "Ready"), size=12, color=COLORS["text_muted"])
        self.detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        self.dd_mode = ft.Dropdown(
            label=_tr("document_pdf_split.mode_label", "Output Type"),
            options=[
                ft.dropdown.Option("pdf", "PDF pages"),
                ft.dropdown.Option("png", "PNG images"),
                ft.dropdown.Option("jpg", "JPEG images"),
            ],
            value=self.state.mode,
            on_change=self.on_param_change,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
        )
        self.tf_dpi = ft.TextField(
            label="DPI",
            value=str(self.state.dpi),
            width=140,
            on_change=self.on_param_change,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            input_filter=ft.NumbersOnlyInputFilter(),
            dense=True,
        )
        self.chk_subfolder = ft.Checkbox(
            label=_tr("document_pdf_split.create_subfolder", "Save output to subfolder"),
            value=True,
            on_change=self.on_param_change,
            scale=0.95,
        )

        self.start_btn = apply_button_sizing(
            ft.ElevatedButton(text="Split", on_click=self.on_start, bgcolor=COLORS["accent"], color=COLORS["text"]),
            "primary",
        )
        self.add_btn = apply_button_sizing(
            ft.OutlinedButton(_tr("common.add", "Add"), icon=ft.Icons.ADD, on_click=self.on_pick_files),
            "compact",
        )
        self.clear_btn = apply_button_sizing(
            ft.OutlinedButton(_tr("common.clear", "Clear"), on_click=self.on_clear_files),
            "compact",
        )
        self.open_btn = apply_button_sizing(
            ft.OutlinedButton(_tr("common.open_folder", "Open Output"), on_click=self.open_output_folder),
            "compact",
        )
        self.source_btn = apply_button_sizing(
            ft.OutlinedButton(_tr("common.open_source", "Source Folder"), on_click=self.open_source_folder),
            "compact",
        )
        self.close_btn = apply_button_sizing(
            ft.OutlinedButton(_tr("common.cancel", "Close"), on_click=self.on_close),
            "compact",
        )

        header = compact_meta_strip(
            title,
            description="Split PDFs into per-page PDF files or image sequences.",
            badges=[self.queue_badge, self.mode_badge, self.output_badge],
        )
        self.files_card = section_card(
            _tr("common.inputs", "Input Files"),
            ft.Container(content=self.file_list, height=300),
            actions=[self.add_btn, self.clear_btn],
        )
        self.settings_card = section_card(
            _tr("common.settings", "Settings"),
            ft.Column(
                [
                    self.dd_mode,
                    ft.Row([ft.Text("DPI"), self.tf_dpi], spacing=SPACING["sm"]),
                    self.chk_subfolder,
                    self.output_hint,
                ],
                spacing=SPACING["sm"],
            ),
        )

        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                padding=SPACING["lg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["md"],
                    controls=[
                        integrated_title_bar(page, title),
                        ft.Container(
                            expand=True,
                            padding=ft.padding.all(SPACING["sm"]),
                            content=ft.Column(
                                expand=True,
                                spacing=SPACING["sm"],
                                controls=[
                                    header,
                                    ft.Row(
                                        expand=True,
                                        spacing=SPACING["md"],
                                        controls=[
                                            ft.Column([self.files_card], expand=3),
                                            ft.Column([self.settings_card], expand=2),
                                        ],
                                    ),
                                    action_bar(
                                        status=ft.Column([self.status_text, self.detail_text], spacing=2, tight=True),
                                        progress=self.progress_bar,
                                        primary=self.start_btn,
                                        secondary=[self.source_btn, self.open_btn, self.close_btn],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            )
        )

        self.state.error = ""
        self.refresh_files()
        self.update_recommendation()
        await reveal_desktop_window(page)

    def _format_mode(self, mode: str) -> str:
        return {"pdf": "PDF", "png": "PNG", "jpg": "JPG"}.get(mode, "PDF")

    def _toggle_dpi_for_pdf_mode(self):
        self.tf_dpi.disabled = self.state.mode == "pdf"
        self.progress_bar.value = 0
        self.progress_bar.visible = False

    def refresh_files(self):
        self.file_list.controls.clear()
        if self.state.files:
            for item in self.state.files:
                self.file_list.controls.append(_file_row(item))
        else:
            self.file_list.controls.append(
                ft.Container(
                    padding=SPACING["lg"],
                    bgcolor=COLORS["surface_alt"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    content=ft.Column(
                        [
                            ft.Text("Drop or add PDF files to start.", size=12, color=COLORS["text_muted"]),
                            ft.Text("Only files already loaded at app start are shown in this session.", size=10, color=COLORS["text_soft"]),
                        ],
                        spacing=6,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        self.queue_badge.content.value = f"{len(self.state.files)} files"
        self.update_recommendation()
        self.page.update()

    def update_recommendation(self):
        mode_label = self._format_mode(self.state.mode)
        self.mode_badge.content.value = mode_label
        if self.state.files:
            first = self.state.files[0]
            out_dir = first.parent / "split_output" if self.chk_subfolder.value else first.parent
            self.output_badge.content.value = str(out_dir)
            self.output_hint.value = f"{self._format_mode(self.state.mode)} will be saved into {out_dir}"
        else:
            self.output_badge.content.value = _tr("document_pdf_split.output_default", "Output folder")
            self.output_hint.value = _tr("document_pdf_split.output_hint", "Output path appears after adding files.")

        self._toggle_dpi_for_pdf_mode()
        if self.start_btn:
            self.start_btn.disabled = self.state.is_processing or not self.state.files

    def on_param_change(self, _):
        self.state.mode = self.dd_mode.value or "pdf"
        try:
            self.state.dpi = max(72, min(1200, int(self.tf_dpi.value or "300")))
            self.tf_dpi.value = str(self.state.dpi)
        except ValueError:
            self.state.dpi = 300
            self.tf_dpi.value = "300"
        self.update_recommendation()
        self.page.update()

    def on_pick_files(self, _):
        if self.file_picker is None:
            return
        self.file_picker.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["pdf"])

    def on_file_result(self, e):
        if not e.files:
            return
        existing = {str(p.resolve()) for p in self.state.files}
        added = False
        for item in e.files:
            path = Path(item.path)
            if not path.exists() or path.suffix.lower() != ".pdf":
                continue
            resolved = str(path.resolve())
            if resolved in existing:
                continue
            self.state.files.append(path)
            existing.add(resolved)
            added = True
        if added:
            self.refresh_files()
            self.page.update()

    def on_clear_files(self, _):
        self.state.files.clear()
        self.state.error = ""
        self.refresh_files()
        self.page.update()

    def open_output_folder(self, _):
        if not self.state.files:
            return
        first = self.state.files[0]
        out_dir = first.parent / "split_output" if self.chk_subfolder.value else first.parent
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        os.startfile(str(out_dir))

    def open_source_folder(self, _):
        if not self.state.files:
            return
        os.startfile(str(self.state.files[0].parent))

    def on_close(self, _):
        self.page.window_close()

    def _run_task(self):
        import traceback

        def on_progress(current: int, total: int, filename: str):
            self.state.progress = current / total if total else 0
            self.state.status_text = f"{current}/{total}"
            self.state.detail_text = filename
            self.page.run_thread(self._refresh_ui)

        def on_complete_local(success: int, total: int, errors: list[str], last_output: Path | None = None):
            self.state.is_processing = False
            self.state.is_cancelled = False
            self.state.progress = 1.0 if total else 0
            self.state.last_output = last_output
            if errors:
                self.state.status_text = _tr("common.completed_with_errors", f"Completed with {len(errors)} error(s).")
                self.state.detail_text = "; ".join(errors[:2])
            else:
                self.state.status_text = f"{success}/{total} " + _tr("common.completed", "completed.")
                self.state.detail_text = _tr("document_pdf_split.completed", "Output ready.")

            def finish_ui():
                self._refresh_ui()
                if errors:
                    dialog = ft.AlertDialog(
                        title=ft.Text(_tr("common.error", "Error")),
                        content=ft.Text(_tr("common.completed_with_errors", "Completed with errors.") + "\n" + "\n".join(errors[:8])),
                        actions=[ft.TextButton("OK", on_click=lambda e: self.page.close(dialog))],
                    )
                else:
                    dialog = ft.AlertDialog(
                        title=ft.Text(_tr("common.success", "Success")),
                        content=ft.Text(self.state.detail_text),
                        actions=[ft.TextButton("OK", on_click=lambda e: self.page.close(dialog))],
                    )
                self.page.open(dialog)
            self.page.run_thread(finish_ui)

        def _run_file_split(pdf_path: Path, out_dir: Path) -> None:
            if self.state.mode == "pdf":
                return split_to_pages(pdf_path, out_dir, on_progress=on_progress)
            fmt = "PNG" if self.state.mode == "png" else "JPEG"
            return split_to_images(pdf_path, out_dir, fmt=fmt, dpi=self.state.dpi, on_progress=on_progress)

        def check_dependencies(mode: str):
            if mode in {"png", "jpg"}:
                try:
                    import pdf2image  # noqa: F401
                except Exception:
                    return False, "Missing dependency: pdf2image"
            try:
                import pypdf  # noqa: F401
            except Exception:
                return False, "Missing dependency: pypdf"
            return True, ""

        ready, message = check_dependencies(self.state.mode)
        if not ready:
            self.state.is_processing = False
            self.state.status_text = message
            self.state.error = message
            self.state.last_output = None
            self.page.run_thread(self._refresh_ui)
            return

        outputs: list[Path] = []
        total = len(self.state.files)
        try:
            for index, source in enumerate(self.state.files):
                if self.state.is_cancelled:
                    break
                out_dir = (source.parent / "split_output" if self.chk_subfolder.value else source.parent)
                out_dir.mkdir(parents=True, exist_ok=True)
                result = _run_file_split(source, out_dir)
                if result:
                    outputs.extend(result)
                on_progress(index + 1, total, source.name)
            on_complete_local(
                success=len(outputs),
                total=total,
                errors=[] if not self.state.error else [self.state.error],
                last_output=outputs[-1] if outputs else None,
            )
        except Exception as exc:
            self.state.error = str(exc)
            self.state.is_processing = False
            self.state.status_text = _tr("common.failed", "Failed")
            self.state.detail_text = str(exc)
            self.page.run_thread(self._refresh_ui)
            self.state.last_output = outputs[-1] if outputs else None
            dialog = ft.AlertDialog(
                title=ft.Text(_tr("common.error", "Error")),
                content=ft.Text(f"{exc}\n{traceback.format_exc()}"),
                actions=[ft.TextButton("OK", on_click=lambda e: self.page.close(dialog))],
            )
            self.page.run_thread(lambda: self.page.open(dialog))

        self.page.run_thread(self._refresh_ui)

    def _refresh_ui(self):
        self.start_btn.disabled = self.state.is_processing or not self.state.files
        self.start_btn.content.value = (
            _tr("common.processing", "Processing...")
            if self.state.is_processing
            else _tr("document_pdf_split.start_btn", "Split")
        )
        self.status_text.value = self.state.status_text
        self.detail_text.value = self.state.detail_text
        self.progress_bar.visible = self.state.is_processing
        self.progress_bar.value = self.state.progress
        self.output_badge.content.value = (
            str(self.state.files[0].parent / "split_output")
            if self.state.files and self.chk_subfolder.value
            else _tr("document_pdf_split.output_folder", "Output folder")
        )
        self.page.update()

    def on_start(self, _):
        if self.state.is_processing or not self.state.files:
            return
        self.state.is_processing = True
        self.state.error = ""
        self.state.status_text = _tr("common.processing", "Processing...")
        self.state.detail_text = ""
        self.state.progress = 0
        self._refresh_ui()
        threading.Thread(target=self._run_task, daemon=True).start()


def start_app(targets: List[str]):
    app = PdfSplitFletApp(targets)
    ft.run(app.main, view=ft.AppView.FLET_APP_HIDDEN)
