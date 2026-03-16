"""Image Converter – Flet UI.

Two-column layout following the reference shell.
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import List, Optional

import flet as ft
from PIL import Image

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

from .service import ImageConvertService
from .state import ImageConvertState


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if not value or value == key else value


def _file_row(src: Path, target_ext: str) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Row(
            [
                ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=COLORS["text_muted"]),
                ft.Text(src.name, size=11, color=COLORS["text_soft"], expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Icon(ft.Icons.ARROW_FORWARD, size=12, color=COLORS["line"]),
                ft.Text(src.with_suffix(target_ext).name, size=11, color=COLORS["accent"], expand=True),
            ],
            spacing=SPACING["sm"],
        ),
    )


def _preview_data_uri(path: Path, size: tuple[int, int] = (320, 180)) -> str | None:
    try:
        with Image.open(path) as img:
            preview = img.convert("RGB")
            preview.thumbnail(size)
            buffer = io.BytesIO()
            preview.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None

def _empty_pick_zone(message: str, on_click) -> ft.Container:
    return ft.Container(
        on_click=on_click,
        padding=SPACING["md"],
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Column(
            [
                ft.Text(message, size=13, color=COLORS["text_muted"], text_align=ft.TextAlign.CENTER),
                ft.Text("Click to add image files.", size=11, color=COLORS["text_soft"], text_align=ft.TextAlign.CENTER),
            ],
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


class ImageConvertFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = ImageConvertService()
        self.state = ImageConvertState(files=[Path(f) for f in initial_files])
        self.file_picker: Optional[ft.FilePicker] = None
        self.folder_picker: Optional[ft.FilePicker] = None
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        self.custom_output_dir: Path | None = None

    async def main(self, page: ft.Page):
        self.page = page
        title = _tr("image_convert_gui.header", "Image Converter")
        configure_page(page, title, window_profile="input_shell")
        page.bgcolor = COLORS["app_bg"]

        if not self.capture_mode:
            self.file_picker = ft.FilePicker(on_result=self.on_file_result)
            self.folder_picker = ft.FilePicker()
            page.overlay.append(self.file_picker)
            page.overlay.append(self.folder_picker)

        # ── controls ──
        self.file_list = ft.ListView(spacing=SPACING["xs"], auto_scroll=False)
        self.preview_image = ft.Image(src="", fit="contain", border_radius=RADII["sm"], visible=False)
        self.preview_empty = ft.Text("Preview appears when exactly one image is selected.", size=11, color=COLORS["text_soft"])
        self.queue_badge = status_badge(f"{len(self.state.files)} files", "muted")
        self.format_badge = status_badge(self.state.target_format, "accent")
        self.output_badge = status_badge("Source folder", "muted")
        self.output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        self.status_text = ft.Text(_tr("common.ready", "Ready"), size=12, color=COLORS["text_muted"])
        self.detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        format_dd = ft.Dropdown(
            label=_tr("image_convert_gui.format_label", "Output Format"),
            options=[ft.dropdown.Option(f) for f in ["PNG", "JPG", "WEBP", "BMP", "TGA", "TIFF", "ICO", "DDS", "EXR"]],
            value="PNG",
            on_select=self.on_format_change,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            expand=True,
        )
        self.resize_combo = ft.Dropdown(
            options=[ft.dropdown.Option(s) for s in ["256", "512", "1024", "2048", "4096"]],
            value="1024",
            on_select=lambda e: setattr(self.state, "resize_size", e.control.value),
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            width=120,
            disabled=True,
        )
        resize_check = ft.Checkbox(label="Resize", on_change=self.on_resize_toggle, scale=0.95)
        save_folder_check = ft.Checkbox(
            label=_tr("image_convert_gui.save_to_folder", "Save to Converted_Images"),
            on_change=self.on_save_folder_toggle,
            scale=0.95,
        )
        self.delete_check = ft.Checkbox(
            label=_tr("image_convert_gui.delete_original", "Delete Originals After Convert"),
            on_change=lambda e: setattr(self.state, "delete_original", e.control.value),
            label_style=ft.TextStyle(color=COLORS["danger"]),
            scale=0.95,
        )

        # ── buttons ──
        self.convert_btn = apply_button_sizing(
            ft.ElevatedButton(
                _tr("image_convert_gui.convert_button", "Convert"),
                on_click=self.on_convert_click,
                bgcolor=COLORS["accent"],
                color=COLORS["text"],
            ),
            "primary",
        )
        add_btn = apply_button_sizing(ft.OutlinedButton("Add", icon=ft.Icons.ADD_PHOTO_ALTERNATE, on_click=self.on_pick_files), "compact")
        clear_btn = apply_button_sizing(ft.OutlinedButton("Clear", on_click=self.on_clear_files), "compact")
        open_output_btn = apply_button_sizing(ft.OutlinedButton("Open", on_click=self.open_output_folder), "compact")
        source_folder_btn = apply_button_sizing(ft.OutlinedButton("Source", on_click=self.use_source_folder), "compact")
        choose_folder_btn = apply_button_sizing(ft.OutlinedButton("Choose", on_click=self.choose_output_folder), "compact")

        self.refresh_files()

        # ── layout ──
        header = compact_meta_strip(
            title,
            description="Convert images between formats with resizing and output path control.",
            badges=[self.queue_badge, self.format_badge, self.output_badge],
        )
        files_card = section_card(
            "Inputs",
            ft.Column(
                [
                    ft.Container(content=self.file_list, height=188),
                    ft.Container(
                        height=128,
                        padding=SPACING["sm"],
                        bgcolor=COLORS["surface_alt"],
                        border=ft.border.all(1, COLORS["line"]),
                        border_radius=RADII["sm"],
                        content=ft.Column(
                            [
                                ft.Text("Preview", size=11, color=COLORS["text_soft"]),
                                ft.Container(
                                    expand=True,
                                    alignment=ft.alignment.Alignment(0, 0),
                                    content=ft.Stack([self.preview_image, self.preview_empty], expand=True),
                                ),
                            ],
                            spacing=SPACING["xs"],
                        ),
                    ),
                ],
                spacing=SPACING["sm"],
            ),
            actions=[add_btn, clear_btn],
        )
        settings_card = section_card(
            "Conversion Settings",
            ft.Column(
                [
                    format_dd,
                    ft.Row([resize_check, self.resize_combo], spacing=SPACING["sm"]),
                    ft.Divider(height=1, color=COLORS["line"]),
                    save_folder_check,
                    self.delete_check,
                    self.output_hint,
                ],
                spacing=SPACING["sm"],
            ),
        )

        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["sm"],
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
                                        spacing=SPACING["sm"],
                                        controls=[
                                            ft.Column([files_card], expand=3),
                                            ft.Column([settings_card], expand=2),
                                        ],
                                    ),
                                    action_bar(
                                        status=ft.Column([self.status_text, self.detail_text], spacing=2, tight=True),
                                        progress=self.progress_bar,
                                        primary=self.convert_btn,
                                        secondary=[open_output_btn, source_folder_btn, choose_folder_btn],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            )
        )
        self.refresh_files()
        self.page.update()
        await reveal_desktop_window(page)

    # ── helpers ──

    def _target_ext(self) -> str:
        fmt = self.state.target_format.lower()
        return f".{fmt}"

    def _sync_output_hint(self):
        if not self.state.files:
            self.output_hint.value = "Output path appears after files are queued."
            return
        src = self.state.files[0]
        if self.custom_output_dir:
            out_dir = self.custom_output_dir
        elif self.state.save_to_folder:
            out_dir = src.parent / "Converted_Images"
        else:
            out_dir = src.parent
        self.output_hint.value = f"{out_dir}\\{src.stem}{self._target_ext()}"

    def refresh_files(self):
        self.file_list.controls.clear()
        ext = self._target_ext()
        if self.state.files:
            for f in self.state.files[:10]:
                self.file_list.controls.append(_file_row(f, ext))
            if len(self.state.files) > 10:
                self.file_list.controls.append(ft.Text(f"... +{len(self.state.files) - 10} more", size=10, color=COLORS["text_soft"]))
        else:
            self.file_list.controls.append(_empty_pick_zone("Add images to see the input list here.", self.on_pick_files))
        self.queue_badge.content.value = f"{len(self.state.files)} files"
        self.format_badge.content.value = self.state.target_format
        if self.custom_output_dir:
            self.output_badge.content.value = "Custom folder"
        elif self.state.save_to_folder:
            self.output_badge.content.value = "Converted_Images"
        else:
            self.output_badge.content.value = "Source folder"
        self.convert_btn.disabled = not self.state.files or self.state.is_converting
        self._sync_output_hint()
        self.detail_text.value = self.output_hint.value
        self._sync_preview()

    def _sync_preview(self):
        if len(self.state.files) == 1:
            preview_src = _preview_data_uri(self.state.files[0])
            self.preview_image.src = preview_src or ""
            self.preview_image.visible = bool(preview_src)
            self.preview_empty.visible = not bool(preview_src)
            if not preview_src:
                self.preview_empty.value = "Preview unavailable for this file."
        elif len(self.state.files) > 1:
            self.preview_image.visible = False
            self.preview_empty.visible = True
            self.preview_empty.value = f"{len(self.state.files)} files selected. Batch mode uses the list above."
        else:
            self.preview_image.visible = False
            self.preview_empty.visible = True
            self.preview_empty.value = "Preview appears when exactly one image is selected."

    # ── event handlers ──

    def on_format_change(self, e):
        self.state.target_format = e.control.value
        self.refresh_files()
        self.page.update()

    def on_resize_toggle(self, e):
        self.state.resize_enabled = e.control.value
        self.resize_combo.disabled = not e.control.value
        self.page.update()

    def on_save_folder_toggle(self, e):
        self.state.save_to_folder = e.control.value
        self.custom_output_dir = None if e.control.value else self.custom_output_dir
        self.refresh_files()
        self.page.update()

    def on_pick_files(self, _):
        if self.file_picker is not None:
            self.file_picker.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE)

    def on_file_result(self, e):
        if not e.files:
            return
        known = {str(path.resolve()) for path in self.state.files}
        for file in e.files:
            path = Path(file.path)
            if not path.exists():
                continue
            resolved = str(path.resolve())
            if resolved in known:
                continue
            self.state.files.append(path)
            known.add(resolved)
        self.refresh_files()
        self.page.update()

    def on_clear_files(self, _):
        self.state.files.clear()
        self.refresh_files()
        self.page.update()

    def open_output_folder(self, _=None):
        if not self.state.files:
            return
        if self.custom_output_dir and self.custom_output_dir.exists():
            os.startfile(str(self.custom_output_dir))
        elif self.state.save_to_folder:
            d = self.state.files[0].parent / "Converted_Images"
            if d.exists():
                os.startfile(str(d))
        else:
            os.startfile(str(self.state.files[0].parent))

    def use_source_folder(self, _=None):
        self.custom_output_dir = None
        self.state.save_to_folder = False
        self.refresh_files()
        self.page.update()

    def choose_output_folder(self, _=None):
        if self.folder_picker is None:
            return
        selected_dir = self.folder_picker.get_directory_path(
            dialog_title="Choose Output Folder",
            initial_directory=str(self.custom_output_dir) if self.custom_output_dir else None,
        )
        if selected_dir:
            self.custom_output_dir = Path(selected_dir)
            self.state.save_to_folder = False
            self.refresh_files()
            self.page.update()

    def on_convert_click(self, _):
        if self.state.is_converting or not self.state.files:
            return
        self.state.is_converting = True
        self.convert_btn.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.status_text.value = "Converting..."
        self.page.update()

        resize_px = int(self.state.resize_size) if self.state.resize_enabled else None

        self.service.convert_batch(
            files=self.state.files,
            target_fmt=self.state.target_format,
            resize_size=resize_px,
            save_to_folder=self.state.save_to_folder,
            delete_original=self.state.delete_original,
            on_progress=self.handle_progress,
            on_complete=self.handle_complete,
        )

    def handle_progress(self, progress, completed, total):
        self.progress_bar.value = progress
        self.status_text.value = f"Processing {completed}/{total}"
        self.page.update()

    def handle_complete(self, success_count, errors):
        self.state.is_converting = False
        self.convert_btn.disabled = False
        self.progress_bar.visible = False
        self.status_text.value = "Conversion complete"

        msg = f"Converted {success_count} images."
        if errors:
            msg += "\n\n" + "\n".join(errors[:5])
        dialog = ft.AlertDialog(
            title=ft.Text("Image Conversion Complete"),
            content=ft.Text(msg),
            actions=[ft.TextButton("OK", on_click=lambda e: self.page.close(dialog))],
        )
        self.page.open(dialog)
        self.page.update()


def start_app(initial_files: List[str]):
    app = ImageConvertFletApp(initial_files)
    ft.run(app.main, view=ft.AppView.FLET_APP_HIDDEN)
