import flet as ft
from pathlib import Path
from typing import List, Optional
import os
import io
import base64
from PIL import Image
import numpy as np

from .service import ImageCompareService
from .state import ImageCompareState
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.layout import apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import apply_desktop_window
from utils.i18n import t

class ImageCompareFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = ImageCompareService()
        self.state = ImageCompareState(files=[Path(f) for f in initial_files])
        
        # UI Controls
        self.canvas_a = ft.Image(src="", fit="contain", gapless_playback=True)
        self.canvas_b = ft.Image(src="", fit="contain", gapless_playback=True)
        self.stats_text = ft.Text(size=12, color=COLORS["accent"])
        self.mode_dropdown = ft.Dropdown(
            width=150,
            options=[
                ft.dropdown.Option("Single"),
                ft.dropdown.Option("Side by Side"),
                ft.dropdown.Option("Slider"),
                ft.dropdown.Option("Difference"),
                ft.dropdown.Option("Grid"),
            ],
            value="Side by Side",
            on_select=self.on_mode_change
        )
        self.channel_dropdown = ft.Dropdown(
            width=100,
            options=[ft.dropdown.Option(c) for c in ["RGB", "R", "G", "B", "A"]],
            value="RGB",
            on_select=self.on_channel_change
        )
        self.slot_a_dropdown = ft.Dropdown(width=200, on_select=lambda e: self.on_slot_change("A", e.control.value))
        self.slot_b_dropdown = ft.Dropdown(width=200, on_select=lambda e: self.on_slot_change("B", e.control.value))
        self.slider_control = ft.Slider(
            value=self.state.slider_pos,
            min=0,
            max=1,
            divisions=100,
            label="{value}",
            on_change=self.on_slider_change,
            visible=False,
        )
        self.file_picker: Optional[ft.FilePicker] = None
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        self.mode_buttons: dict[str, ft.Control] = {}

    def main(self, page: ft.Page):
        self.page = page
        configure_page(page, t("image_compare_gui.title"), window_profile="wide_canvas")
        if not self.capture_mode:
            self.file_picker = ft.FilePicker()
            page.overlay.append(self.file_picker)
        page.update()
        
        self.setup_ui()
        self.load_initial_data()
        self.update_ui()

    def setup_ui(self):
        summary_bar = ft.Container(
            content=ft.Row([
                ft.Text("이미지 두 개를 선택해 비교 모드를 바꾸며 차이를 확인합니다.", color=COLORS["text_muted"], expand=True),
                self.stats_text,
            ], alignment="spaceBetween"),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
        )

        self.mode_selector = ft.Row(
            controls=[
                self._create_mode_button("Single", "Single"),
                self._create_mode_button("Side by Side", "Split"),
                self._create_mode_button("Slider", "Slider"),
                self._create_mode_button("Difference", "Diff"),
            ],
            spacing=8,
            wrap=True,
        )

        toolbar = ft.Container(
            content=ft.Row([
                apply_button_sizing(ft.ElevatedButton("이미지 추가", icon=ft.Icons.ADD, on_click=self.on_add_click), "toolbar"),
                self.mode_selector,
                self.channel_dropdown,
                ft.Container(expand=True),
                ft.Text("A", color=COLORS["text_muted"]),
                self.slot_a_dropdown,
                ft.Text("B", color=COLORS["text_muted"]),
                self.slot_b_dropdown,
            ], spacing=SPACING["md"], wrap=True),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
            bgcolor=COLORS["surface_alt"],
            border_radius=RADII["md"],
        )

        # Main View Area
        self.view_container = ft.Stack(expand=True)
        
        # Wrap everything in a gesture detector for pan/zoom
        self.gesture_detector = ft.GestureDetector(
            content=self.view_container,
            on_pan_update=self.on_pan,
            on_scroll=self.on_scroll,
            multi_tap_touches=2,
        )

        # Footer
        footer = ft.Container(
            content=ft.Row([
                ft.Text("Space/Tab: Toggle A/B | Drag: Pan | Scroll: Zoom", size=10, color=COLORS["text_soft"]),
                ft.Row([
                    ft.IconButton(ft.Icons.EDIT, on_click=lambda _: self.reset_view(), tooltip="Reset View"),
                    ft.IconButton(ft.Icons.ZOOM_OUT, on_click=lambda _: self.adjust_zoom(0.8)),
                    ft.IconButton(ft.Icons.ZOOM_IN, on_click=lambda _: self.adjust_zoom(1.2)),
                ])
            ], alignment="spaceBetween"),
            padding=ft.padding.symmetric(horizontal=SPACING["md"]),
            bgcolor=COLORS["surface_soft"],
        )

        self.page.add(
            ft.Container(
                content=ft.Column([
                    summary_bar,
                    toolbar,
                    ft.Container(self.gesture_detector, expand=True, bgcolor="#000000", border_radius=RADII["md"]),
                    ft.Container(self.slider_control, padding=ft.padding.symmetric(horizontal=SPACING["md"])),
                    footer,
                ], expand=True),
                padding=SPACING["xl"],
                expand=True,
            )
        )
        self._sync_mode_buttons()

    def _create_mode_button(self, mode: str, label: str):
        button = ft.OutlinedButton(
            label,
            on_click=lambda _, value=mode: self.set_mode(value),
            height=36,
        )
        button.width = 92
        self.mode_buttons[mode] = button
        return button

    def _sync_mode_buttons(self):
        for mode, button in self.mode_buttons.items():
            active = mode == self.state.current_mode
            button.style = ft.ButtonStyle(
                bgcolor=COLORS["accent"] if active else COLORS["surface"],
                color=COLORS["text"] if active else COLORS["text_muted"],
                side=ft.BorderSide(1, COLORS["accent"] if active else COLORS["line"]),
                shape=ft.RoundedRectangleBorder(radius=RADII["pill"]),
            )

    def load_initial_data(self):
        if self.state.files:
            # Load EXR channels if applicable
            exr_channels = self.service.get_exr_channels(str(self.state.files[0]))
            if exr_channels:
                all_channels = ["RGB", "R", "G", "B", "A"] + [c for c in exr_channels if c not in "RGBArgba"]
                self.channel_dropdown.options = [ft.dropdown.Option(c) for c in all_channels]
            
            self.update_dropdown_options()
            
            # Default slots
            self.state.slots["A"] = 0
            self.state.slots["B"] = 1 if len(self.state.files) > 1 else 0
            self.sync_dropdowns()

    def update_dropdown_options(self):
        options = [ft.dropdown.Option(key=str(i), text=f"{i+1}: {f.name}") for i, f in enumerate(self.state.files)]
        self.slot_a_dropdown.options = options
        self.slot_b_dropdown.options = options
        self.page.update()

    def sync_dropdowns(self):
        self.slot_a_dropdown.value = str(self.state.slots["A"])
        self.slot_b_dropdown.value = str(self.state.slots["B"])
        self.page.update()

    def update_ui(self):
        self.view_container.controls.clear()
        
        mode = self.state.current_mode
        idx_a = self.state.slots["A"]
        idx_b = self.state.slots["B"]
        
        path_a = str(self.state.files[idx_a]) if idx_a < len(self.state.files) else None
        path_b = str(self.state.files[idx_b]) if idx_b < len(self.state.files) else None
        
        if not path_a:
            self.view_container.controls.append(
                ft.Row([ft.Text("No Images Loaded", color=COLORS["text_muted"])], alignment="center")
            )
        else:
            if mode == "Single":
                active_idx = self.state.slots[self.state.active_slot]
                path = str(self.state.files[active_idx])
                self.view_container.controls.append(self.create_image_control(path))
            
            elif mode == "Side by Side":
                col = ft.Row([
                    ft.Container(self.create_image_control(path_a), expand=True),
                    ft.Container(self.create_image_control(path_b), expand=True) if path_b else ft.Container(expand=True)
                ], expand=True, spacing=0)
                self.view_container.controls.append(col)
                
            elif mode == "Slider":
                if path_a and path_b:
                    slider_img = self.create_slider_preview(path_a, path_b)
                    if slider_img is not None:
                        self.view_container.controls.append(self.create_image_control_from_pil(slider_img))
                    else:
                        self.view_container.controls.append(self.create_image_control(path_a))
                else:
                    self.view_container.controls.append(self.create_image_control(path_a))
                
            elif mode == "Difference":
                if path_a and path_b:
                    diff_pil = self.service.get_diff_image(path_a, path_b, self.state.current_channel)
                    if diff_pil:
                        self.view_container.controls.append(self.create_image_control_from_pil(diff_pil))
        
        # Update metrics
        if path_a and path_b:
            ssim, diff = self.service.compute_metrics(path_a, path_b, self.state.current_channel)
            self.stats_text.value = f"SSIM: {ssim:.4f} | Diff: {diff:,}" if ssim is not None else ""
        else:
            self.stats_text.value = ""

        self.slider_control.visible = mode == "Slider" and bool(path_a and path_b)
        self.slider_control.value = self.state.slider_pos
        self._sync_mode_buttons()
        
        self.page.update()

    def set_mode(self, mode: str):
        self.state.current_mode = mode
        self.mode_dropdown.value = mode
        self.update_ui()

    def create_image_control(self, path: str):
        pil_img = self.service.get_pil_image(path, self.state.current_channel)
        if not pil_img:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.BROKEN_IMAGE_OUTLINED, size=32, color=COLORS["text_muted"]),
                    ft.Text("미리보기를 불러올 수 없습니다.", color=COLORS["text_muted"]),
                    ft.Text(Path(path).name, size=11, color=COLORS["text_soft"]),
                ], horizontal_alignment="center", alignment="center"),
                alignment=ft.alignment.center,
                expand=True,
            )
        return self.create_image_control_from_pil(pil_img)

    def create_image_control_from_pil(self, pil_img: Image.Image):
        buffered = io.BytesIO()
        pil_img.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        encoded = base64.b64encode(img_bytes).decode("ascii")
        return ft.Image(
            src=f"data:image/png;base64,{encoded}",
            scale=self.state.zoom_level,
            offset=ft.Offset(self.state.pan_offset[0], self.state.pan_offset[1]),
            animate_offset=ft.Animation(100, "decelerate"),
            animate_scale=ft.Animation(100, "decelerate"),
        )

    def on_mode_change(self, e):
        self.set_mode(e.control.value)

    def on_channel_change(self, e):
        self.state.current_channel = e.control.value
        self.update_ui()

    def on_slot_change(self, slot, value):
        self.state.slots[slot] = int(value)
        self.update_ui()

    def on_slider_change(self, e):
        self.state.slider_pos = float(e.control.value)
        if self.state.current_mode == "Slider":
            self.update_ui()

    def on_pan(self, e: ft.DragUpdateEvent):
        # Very simple pan
        self.state.pan_offset[0] += e.delta_x / 500
        self.state.pan_offset[1] += e.delta_y / 500
        # Re-render images to update offset (Flet optimization: we might need to update only the image control)
        self.update_ui()

    def on_scroll(self, e: ft.ScrollEvent):
        if e.scroll_delta_y < 0:
            self.adjust_zoom(1.1)
        else:
            self.adjust_zoom(0.9)

    def adjust_zoom(self, factor):
        self.state.zoom_level = max(0.1, min(10.0, self.state.zoom_level * factor))
        self.update_ui()

    def reset_view(self):
        self.state.reset_view()
        self.update_ui()

    def on_add_click(self, _):
        if self.file_picker is None:
            return
        files = self.file_picker.pick_files(
            allow_multiple=True,
            file_type=ft.FilePickerFileType.IMAGE,
            allowed_extensions=["png", "jpg", "jpeg", "bmp", "tga", "tif", "tiff", "webp", "exr"],
        )
        if not files:
            return
        known = {str(path.resolve()) for path in self.state.files}
        for file in files:
            path = Path(file.path)
            if not path.exists():
                continue
            resolved = str(path.resolve())
            if resolved in known:
                continue
            self.state.files.append(path)
            known.add(resolved)
        if self.state.files:
            self.update_dropdown_options()
            if self.state.slots["A"] >= len(self.state.files):
                self.state.slots["A"] = 0
            if self.state.slots["B"] >= len(self.state.files):
                self.state.slots["B"] = 1 if len(self.state.files) > 1 else 0
            self.sync_dropdowns()
        self.update_ui()

    def create_slider_preview(self, path_a: str, path_b: str) -> Optional[Image.Image]:
        img_a = self.service.get_pil_image(path_a, self.state.current_channel)
        img_b = self.service.get_pil_image(path_b, self.state.current_channel)
        if img_a is None or img_b is None:
            return None

        if img_b.size != img_a.size:
            img_b = img_b.resize(img_a.size, Image.Resampling.LANCZOS)

        arr_a = np.array(img_a)
        arr_b = np.array(img_b)
        cut = max(0, min(arr_a.shape[1], int(arr_a.shape[1] * self.state.slider_pos)))
        combined = arr_b.copy()
        combined[:, :cut] = arr_a[:, :cut]

        # Add a visible split line.
        if 0 <= cut < combined.shape[1]:
            combined[:, cut:cut + 2] = [255, 255, 255]

        return Image.fromarray(combined)

def start_app(initial_files: List[str]):
    app = ImageCompareFletApp(initial_files)
    ft.app(target=app.main)
