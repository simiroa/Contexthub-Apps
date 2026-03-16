"""POT Image Resize – Flet UI.

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

from .service import ResizePotService
from .state import ResizePotState


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if not value or value == key else value


def _file_row(src: Path) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Row(
            [
                ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=COLORS["text_muted"]),
                ft.Text(src.name, size=12, color=COLORS["text"], expand=True, no_wrap=True),
                ft.Text(src.suffix.upper().lstrip("."), size=10, color=COLORS["text_soft"]),
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


class ResizePotFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = ResizePotService()
        self.state = ResizePotState(files=[Path(f) for f in initial_files if Path(f).exists()])
        self.current_img_size = (0, 0)
        if self.state.files:
            try:
                with Image.open(self.state.files[0]) as img:
                    self.current_img_size = img.size
            except Exception:
                pass

    async def main(self, page: ft.Page):
        self.page = page
        title = _tr("image_resize_gui.title", "POT Image Resize")
        configure_page(page, title, window_profile="input_shell")
        page.bgcolor = COLORS["app_bg"]
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        if not self.capture_mode:
            self.file_picker = ft.FilePicker(on_result=self.on_file_result)
            page.overlay.append(self.file_picker)
        else:
            self.file_picker = None

        # ── controls ──
        self.file_list = ft.ListView(spacing=SPACING["xs"], auto_scroll=False)
        self.preview_image = ft.Image(src="", fit="contain", border_radius=RADII["sm"], visible=False)
        self.preview_empty = ft.Text("Preview appears when exactly one image is selected.", size=11, color=COLORS["text_soft"])
        self.queue_badge = status_badge(f"{len(self.state.files)} files", "muted")
        self.target_badge = status_badge(f"{self.state.target_size}px", "accent")
        self.output_badge = status_badge("Source folder", "muted")
        self.output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        self.info_text = ft.Text("", size=12, color=COLORS["text_muted"])

        self.status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        self.detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        self.dd_size = ft.Dropdown(
            label=_tr("image_resize_gui.target_resolution", "Target Size"),
            options=[ft.dropdown.Option(s) for s in ["512", "1024", "2048", "4096", "8192"]],
            value=self.state.target_size,
            on_select=self.on_param_change,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            expand=True,
        )
        self.chk_square = ft.Checkbox(
            label=_tr("image_resize_gui.force_square", "Force Square (Padding)"),
            value=self.state.force_square,
            on_change=self.on_param_change,
            scale=0.95,
        )
        self.rg_mode = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="Standard", label="Standard (Lanczos)"),
                ft.Radio(value="AI", label="AI Upscale"),
            ], spacing=SPACING["md"]),
            value=self.state.mode,
            on_change=self.on_param_change,
        )
        self.chk_folder = ft.Checkbox(label="Save to subfolder", value=self.state.save_to_folder, on_change=self.on_param_change, scale=0.95)
        self.chk_delete = ft.Checkbox(label="Delete originals", value=self.state.delete_original, on_change=self.on_param_change, scale=0.95)

        self.run_btn = apply_button_sizing(
            ft.ElevatedButton("Resize", on_click=self.on_run_click, bgcolor=COLORS["accent"], color=COLORS["text"]),
            "primary",
        )
        add_btn = apply_button_sizing(ft.OutlinedButton("Add", icon=ft.Icons.ADD_PHOTO_ALTERNATE, on_click=self.on_pick_files), "compact")
        clear_btn = apply_button_sizing(ft.OutlinedButton("Clear", on_click=self.on_clear_files), "compact")
        open_output_btn = apply_button_sizing(ft.OutlinedButton("Open", on_click=self.open_output_folder), "compact")

        self.refresh_files()
        self.update_recommendation()

        header = compact_meta_strip(
            title,
            description="Resize images to the nearest power-of-two dimension.",
            badges=[self.queue_badge, self.target_badge, self.output_badge],
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
            "Settings",
            ft.Column(
                [
                    self.dd_size,
                    self.chk_square,
                    ft.Divider(height=1, color=COLORS["line"]),
                    ft.Text("Resize Method", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    self.rg_mode,
                    ft.Container(
                        content=self.info_text,
                        padding=SPACING["sm"],
                        bgcolor=COLORS["surface_alt"],
                        border_radius=RADII["sm"],
                    ),
                    ft.Divider(height=1, color=COLORS["line"]),
                    self.chk_folder,
                    self.chk_delete,
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
                                        primary=self.run_btn,
                                        secondary=[open_output_btn],
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

    def refresh_files(self):
        self.file_list.controls.clear()
        if self.state.files:
            for src in self.state.files:
                self.file_list.controls.append(_file_row(src))
        else:
            self.file_list.controls.append(_empty_pick_zone("Add images to resize in the list above.", self.on_pick_files))
        self.queue_badge.content.value = f"{len(self.state.files)} files"
        self.run_btn.disabled = not self.state.files or self.state.is_processing
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

    def on_pick_files(self, _):
        if self.file_picker is not None:
            self.file_picker.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE)

    def on_file_result(self, e):
        if not e.files:
            return
        known = {str(path.resolve()) for path in self.state.files}
        added = False
        for file in e.files:
            path = Path(file.path)
            if not path.exists():
                continue
            resolved = str(path.resolve())
            if resolved in known:
                continue
            self.state.files.append(path)
            known.add(resolved)
            added = True
        if added and self.current_img_size == (0, 0):
            try:
                with Image.open(self.state.files[0]) as img:
                    self.current_img_size = img.size
            except Exception:
                pass
        self.refresh_files()
        self.update_recommendation()
        self.page.update()

    def on_clear_files(self, _):
        self.state.files.clear()
        self.current_img_size = (0, 0)
        self.refresh_files()
        self.update_recommendation()
        self.page.update()

    def on_param_change(self, _):
        self.state.target_size = self.dd_size.value or "1024"
        self.state.force_square = bool(self.chk_square.value)
        self.state.mode = self.rg_mode.value or "Standard"
        self.state.save_to_folder = bool(self.chk_folder.value)
        self.state.delete_original = bool(self.chk_delete.value)
        self.target_badge.content.value = f"{self.state.target_size}px"
        self.update_recommendation()
        self.page.update()

    def update_recommendation(self):
        target = int(self.state.target_size)
        current = max(self.current_img_size) if self.current_img_size[0] > 0 else 1024
        ratio = target / current

        msg = f"Current largest side: ~{current}px → Target: {target}px\n"
        color = COLORS["text_muted"]

        if ratio > 1.5:
            msg += f"Upscale: {ratio:.1f}x\n"
            if self.state.mode != "AI":
                msg += "Tip: Use AI Upscale for better quality."
                color = COLORS["warning"]
            else:
                msg += "AI Upscale selected."
                color = COLORS.get("success", COLORS["accent"])
        elif ratio < 0.8:
            msg += f"Downscale: {ratio:.1f}x"
        else:
            msg += "Size change is minimal."

        self.info_text.value = msg
        self.info_text.color = color

        if self.state.files:
            src = self.state.files[0]
            if self.state.save_to_folder:
                self.output_hint.value = f"{src.parent}\\Resized\\{src.stem}_{target}{src.suffix}"
            else:
                self.output_hint.value = f"{src.parent}\\{src.stem}_{target}{src.suffix}"
        else:
            self.output_hint.value = "Output path appears after files are queued."

    def open_output_folder(self, _=None):
        if not self.state.files:
            return
        out_dir = self.state.files[0].parent
        if self.state.save_to_folder:
            d = out_dir / "Resized"
            if d.exists():
                out_dir = d
        os.startfile(str(out_dir))

    def on_run_click(self, _):
        if self.state.is_processing or not self.state.files:
            return
        self.state.is_processing = True
        self.run_btn.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.page.update()

        self.service.run_resize_batch(
            files=self.state.files,
            target_size=int(self.state.target_size),
            mode=self.state.mode,
            force_square=self.state.force_square,
            save_to_folder=self.state.save_to_folder,
            delete_original=self.state.delete_original,
            on_progress=self.handle_progress,
            on_complete=self.handle_complete,
        )

    def handle_progress(self, progress, status):
        self.progress_bar.value = progress
        self.status_text.value = status
        self.page.update()

    def handle_complete(self, success_count, errors):
        self.state.is_processing = False
        self.run_btn.disabled = False
        self.progress_bar.visible = False

        msg = f"Processed {success_count} images."
        if errors:
            msg += "\n\n" + "\n".join(errors[:5])
        self.status_text.value = f"Resized {success_count} file(s)." if not errors else f"Completed with {len(errors)} error(s)."
        dialog = ft.AlertDialog(
            title=ft.Text("Resize Complete"),
            content=ft.Text(msg),
            actions=[ft.TextButton("OK", on_click=lambda e: self.page.close(dialog))],
        )
        self.page.open(dialog)
        self.page.update()


def start_app(targets: List[str]):
    app = ResizePotFletApp(targets)
    ft.run(app.main, view=ft.AppView.FLET_APP_HIDDEN)
