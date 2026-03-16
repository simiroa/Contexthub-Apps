from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import List

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
from .service import SimplePbrService
from .state import PbrGenState
from utils.i18n import t


EMPTY_PNG_DATA_URI = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X2x0AAAAASUVORK5CYII="
)

def _file_row(src: Path) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        border_radius=RADII["sm"],
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=COLORS["text_muted"]),
                ft.Text(src.name, size=12, color=COLORS["text"], expand=True, no_wrap=True),
                ft.Text(src.suffix.upper().lstrip("."), size=10, color=COLORS["text_soft"]),
            ],
            spacing=SPACING["sm"],
        ),
    )


class SimplePbrFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = SimplePbrService()
        self.state = PbrGenState(files=[Path(f) for f in initial_files if Path(f).exists()])
        self.original_img: Image.Image | None = None
        self.folder_picker: ft.FilePicker | None = None
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        if self.state.files:
            try:
                self.original_img = Image.open(self.state.files[0]).convert("RGB")
            except Exception:
                self.original_img = None

    async def main(self, page: ft.Page):
        self.page = page
        title = t("image_simple_pbr.title")
        if not title or title == "image_simple_pbr.title":
            title = "PBR Map Generator"
        configure_page(page, title, window_profile="form")
        page.bgcolor = COLORS["app_bg"]
        if not self.capture_mode:
            self.folder_picker = ft.FilePicker()
            page.overlay.append(self.folder_picker)

        self.preview_image = ft.Image(src=EMPTY_PNG_DATA_URI, fit="contain", border_radius=RADII["md"])
        self.queue_badge = status_badge(f"{len(self.state.files)} files", "muted")
        self.preview_badge = status_badge(self.state.preview_mode, "accent")
        self.output_badge = status_badge("Source folder", "muted")
        self.save_badge = status_badge(self.state.save_mode, "accent")
        self.output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        self.status_text = ft.Text(self.state.status_text, size=12, color=COLORS["text_muted"])
        self.detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])
        self.file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)

        self.preview_tabs = ft.SegmentedButton(
            segments=[
                ft.Segment(value="Original", label=ft.Text("Original")),
                ft.Segment(value="Normal", label=ft.Text("Normal")),
                ft.Segment(value="Roughness", label=ft.Text("Roughness")),
            ],
            selected=[self.state.preview_mode],
            on_change=self.on_preview_mode_change,
        )
        self.save_mode_dropdown = ft.Dropdown(
            label="Save Output",
            value=self.state.save_mode,
            options=[ft.dropdown.Option("Normal"), ft.dropdown.Option("Roughness"), ft.dropdown.Option("Both")],
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            expand=True,
        )
        self.normal_slider = ft.Slider(min=0.1, max=5.0, value=self.state.normal_strength, divisions=49, label="{value}")
        self.flip_green_check = ft.Checkbox(label="Flip Green (DirectX)", value=self.state.normal_flip_g, scale=0.95)
        self.roughness_slider = ft.Slider(min=0.1, max=3.0, value=self.state.roughness_contrast, divisions=29, label="{value}")
        self.invert_check = ft.Checkbox(label="Invert Roughness", value=self.state.roughness_invert, scale=0.95)

        self.run_button = apply_button_sizing(ft.ElevatedButton("Save Maps", on_click=self.on_save_click, bgcolor=COLORS["accent"], color=COLORS["text"]), "primary")
        self.cancel_button = apply_button_sizing(ft.OutlinedButton("Cancel", on_click=self.on_cancel_click, disabled=True), "compact")
        self.open_output_button = apply_button_sizing(ft.OutlinedButton("Open Output", on_click=self.open_output_folder), "compact")
        self.source_folder_button = apply_button_sizing(ft.OutlinedButton("Source Folder", on_click=self.use_source_folder), "compact")
        self.choose_folder_button = apply_button_sizing(ft.OutlinedButton("Choose Folder", on_click=self.choose_output_folder), "compact")

        self.normal_slider.on_change = self.on_param_change
        self.flip_green_check.on_change = self.on_param_change
        self.roughness_slider.on_change = self.on_param_change
        self.invert_check.on_change = self.on_param_change
        self.save_mode_dropdown.on_select = self.on_save_mode_change

        header = compact_meta_strip(
            title,
            badges=[self.queue_badge, self.preview_badge, self.save_badge, self.output_badge],
        )
        files_card = section_card("Input", ft.Container(content=self.file_list, height=220))
        preview_card = section_card(
            "Preview",
            ft.Column(
                [
                    self.preview_tabs,
                    ft.Container(
                        height=300,
                        border_radius=RADII["md"],
                        bgcolor=COLORS["surface_alt"],
                        border=ft.border.all(1, COLORS["line"]),
                        alignment=ft.alignment.Alignment(0, 0),
                        content=self.preview_image,
                    ),
                ],
                spacing=SPACING["sm"],
            ),
        )
        params_card = section_card(
            "Parameters",
            ft.Column(
                [
                    self.save_mode_dropdown,
                    ft.Text("Normal Strength", size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    self.normal_slider,
                    self.flip_green_check,
                    ft.Text("Roughness Contrast", size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    self.roughness_slider,
                    self.invert_check,
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
                                            ft.Column([files_card, preview_card], expand=3),
                                            ft.Column([params_card], expand=2),
                                        ],
                                    ),
                                    action_bar(
                                        status=ft.Column([self.status_text, self.detail_text], spacing=2, tight=True),
                                        progress=self.progress_bar,
                                        primary=self.run_button,
                                        secondary=[
                                            self.source_folder_button,
                                            self.choose_folder_button,
                                            self.open_output_button,
                                            self.cancel_button,
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            )
        )

        self.refresh_files()
        self.update_preview()
        self.update_ui()
        await reveal_desktop_window(page)

    def _params(self) -> dict:
        return {
            "normal_strength": self.state.normal_strength,
            "normal_flip_g": self.state.normal_flip_g,
            "roughness_contrast": self.state.roughness_contrast,
            "roughness_invert": self.state.roughness_invert,
        }

    def _resolve_output_dir(self) -> Path | None:
        if self.state.custom_output_dir:
            return self.state.custom_output_dir
        if not self.state.files:
            return None
        return self.state.files[0].parent

    def _output_summary(self) -> str:
        if not self.state.files:
            return "Output path appears after an image is queued."
        out_dir = self._resolve_output_dir()
        if not out_dir:
            return "Output path unavailable."
        stem = self.state.files[0].stem
        if self.state.save_mode == "Normal":
            return f"{out_dir}\\{stem}_normal.png"
        if self.state.save_mode == "Roughness":
            return f"{out_dir}\\{stem}_roughness.png"
        return f"{out_dir}\\{stem}_normal.png + {stem}_roughness.png"

    def refresh_files(self):
        self.file_list.controls.clear()
        if self.state.files:
            for src in self.state.files:
                self.file_list.controls.append(_file_row(src))
        else:
            self.file_list.controls.append(
                ft.Container(
                    padding=SPACING["md"],
                    border_radius=RADII["sm"],
                    border=ft.border.all(1, COLORS["line"]),
                    bgcolor=COLORS["surface_alt"],
                    content=ft.Text("No source image yet. Launch from the context menu on one image or a small batch.", color=COLORS["text_muted"]),
                )
            )

    def update_ui(self):
        self.queue_badge.content.value = f"{len(self.state.files)} files"
        self.preview_badge.content.value = self.state.preview_mode
        self.save_badge.content.value = self.state.save_mode
        if self.state.custom_output_dir:
            self.output_badge.content.value = "Custom folder"
        else:
            self.output_badge.content.value = "Source folder"
        self.output_hint.value = self._output_summary()
        self.status_text.value = self.state.status_text
        self.detail_text.value = self.state.detail_text or self.output_hint.value
        self.progress_bar.visible = self.state.is_processing or self.state.progress > 0
        self.progress_bar.value = self.state.progress
        self.run_button.disabled = self.state.is_processing or not self.state.files or self.state.preview_mode == "Original"
        self.cancel_button.disabled = not self.state.is_processing
        self.open_output_button.disabled = (self.state.last_output_dir or self._resolve_output_dir()) is None
        self.page.update()

    def on_preview_mode_change(self, e):
        selection = list(e.selection)
        self.state.preview_mode = selection[0] if selection else "Original"
        if self.state.preview_mode in {"Normal", "Roughness"}:
            self.state.save_mode = self.state.preview_mode
            self.save_mode_dropdown.value = self.state.save_mode
        self.update_preview()
        self.update_ui()

    def on_save_mode_change(self, e):
        self.state.save_mode = e.control.value or "Normal"
        self.update_ui()

    def on_param_change(self, _):
        self.state.normal_strength = float(self.normal_slider.value)
        self.state.normal_flip_g = bool(self.flip_green_check.value)
        self.state.roughness_contrast = float(self.roughness_slider.value)
        self.state.roughness_invert = bool(self.invert_check.value)
        self.update_preview()
        self.update_ui()

    def update_preview(self):
        if not self.original_img:
            return
        norm, rough = self.service.generate_maps(self.original_img, self._params())
        target = self.original_img
        if self.state.preview_mode == "Normal":
            target = norm
        elif self.state.preview_mode == "Roughness":
            target = rough
        display = target.copy()
        display.thumbnail((900, 900))
        encoded = base64.b64encode(self.service.get_preview_bytes(display)).decode("ascii")
        self.preview_image.src = f"data:image/png;base64,{encoded}"
        self.page.update()

    def use_source_folder(self, _=None):
        self.state.custom_output_dir = None
        self.update_ui()

    def choose_output_folder(self, _=None):
        if self.folder_picker is None:
            return
        selected_dir = self.folder_picker.get_directory_path(
            dialog_title="Choose Output Folder",
            initial_directory=str(self.state.custom_output_dir) if self.state.custom_output_dir else None,
        )
        if selected_dir:
            self.state.custom_output_dir = Path(selected_dir)
            self.update_ui()

    def open_output_folder(self, _=None):
        out_dir = self.state.last_output_dir or self._resolve_output_dir()
        if out_dir and out_dir.exists():
            os.startfile(str(out_dir))

    def on_save_click(self, _):
        if self.state.is_processing or not self.state.files:
            return
        self.state.is_processing = True
        self.state.progress = 0
        self.state.status_text = "Saving maps..."
        self.state.detail_text = self._output_summary()
        self.update_ui()

        self.service.run_batch_save(
            files=self.state.files,
            params=self._params(),
            mode=self.state.save_mode,
            output_dir=self.state.custom_output_dir,
            on_progress=self.handle_progress,
            on_complete=self.handle_complete,
        )

    def on_cancel_click(self, _):
        if not self.state.is_processing:
            return
        self.service.cancel()
        self.state.status_text = "Cancelling..."
        self.update_ui()

    def handle_progress(self, progress, status):
        self.state.progress = progress
        self.state.status_text = status
        self.page.update()

    def handle_complete(self, success_count, errors, output_dir):
        self.state.is_processing = False
        self.state.progress = 1.0 if success_count and not errors else 0.0
        self.state.last_output_dir = output_dir or self._resolve_output_dir()
        if not errors:
            label = self.state.save_mode.lower()
            self.state.status_text = f"Saved {success_count} {label} output set(s)."
            self.state.detail_text = self._output_summary()
        else:
            self.state.status_text = f"Completed with {len(errors)} error(s)."
            self.state.detail_text = errors[0]
        self.update_ui()


def start_app(targets: List[str]):
    app = SimplePbrFletApp(targets)
    ft.run(app.main, view=ft.AppView.FLET_APP_HIDDEN)
