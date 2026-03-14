import flet as ft
from pathlib import Path
from typing import List, Optional
import base64
from PIL import Image

from .service import SimplePbrService
from .state import PbrGenState
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import apply_desktop_window
from utils.i18n import t

EMPTY_PNG_DATA_URI = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X2x0AAAAASUVORK5CYII="
)

class SimplePbrFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = SimplePbrService()
        self.state = PbrGenState(files=[Path(f) for f in initial_files if Path(f).exists()])
        
        self.original_img = None
        if self.state.files:
            try:
                self.original_img = Image.open(self.state.files[0]).convert("RGB")
            except: pass

    def main(self, page: ft.Page):
        self.page = page
        title = t("image_simple_pbr.title") or "PBR Map Generator"
        configure_page(page, title, window_profile="two_pane")
        page.update()
        
        self.setup_controls()
        self.setup_ui()
        self.update_preview()

    def setup_controls(self):
        # Preview Area
        self.img_preview = ft.Image(
            src=EMPTY_PNG_DATA_URI,
            fit="contain",
            border_radius=RADII["md"],
        )
        
        # Mode Selector
        self.mode_selector = ft.SegmentedButton(
            segments=[
                ft.Segment(value="Original", label=ft.Text("Original")),
                ft.Segment(value="Normal", label=ft.Text("Normal")),
                ft.Segment(value="Roughness", label=ft.Text("Roughness")),
            ],
            selected=[self.state.preview_mode],
            on_change=self.on_mode_change,
        )

        # Normal Controls
        self.sl_normal = ft.Slider(min=0.1, max=5.0, value=1.0, divisions=49, label="{value}", on_change=self.on_param_change)
        self.chk_flip_g = ft.Checkbox(label="Flip Green (DirectX)", value=False, on_change=self.on_param_change)
        self.normal_panel = ft.Column([
            ft.Text("Normal Strength", size=12, weight="bold"),
            self.sl_normal,
            self.chk_flip_g
        ], spacing=2)

        # Roughness Controls
        self.sl_rough = ft.Slider(min=0.1, max=3.0, value=1.0, divisions=29, label="{value}", on_change=self.on_param_change)
        self.chk_invert = ft.Checkbox(label="Invert Roughness", value=False, on_change=self.on_param_change)
        self.roughness_panel = ft.Column([
            ft.Text("Roughness Contrast", size=12, weight="bold"),
            self.sl_rough,
            self.chk_invert
        ], spacing=2)

        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        
        self.btn_save = ft.ElevatedButton(
            "Save Normal Map(s)",
            icon="save",
            on_click=self.on_save_click,
            bgcolor=COLORS["accent"],
            color=COLORS["text"],
            height=50,
            expand=True
        )

    def setup_ui(self):
        header = ft.Container(
            content=ft.Column([
                ft.Text(t("image_simple_pbr.title") or "PBR Map Generator", size=22, weight="bold"),
                ft.Text("Preview one generated map, tweak the controls, then save the selected output.", size=12, color=COLORS["text_muted"]),
            ]),
            padding=ft.padding.only(bottom=SPACING["md"])
        )

        summary_bar = ft.Container(
            content=ft.Row([
                ft.Text(f"입력 파일 {len(self.state.files)}개", color=COLORS["text_muted"]),
                ft.VerticalDivider(width=16, color="transparent"),
                self.status_text,
            ], wrap=True),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
        )

        preview_container = ft.Container(
            content=ft.Column([
                ft.Text("미리보기", weight="bold"),
                ft.Container(
                    content=self.img_preview,
                    expand=True,
                    alignment=ft.alignment.Alignment(0, 0),
                ),
            ], spacing=SPACING["sm"]),
            expand=True,
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
            padding=SPACING["md"],
        )

        controls_container = ft.Container(
            content=ft.Column([
                ft.Text("출력 선택", weight="bold"),
                ft.Row([self.mode_selector], alignment=ft.MainAxisAlignment.CENTER),
                ft.Text("`Normal`과 `Roughness` 중 저장할 대상을 선택하세요.", size=12, color=COLORS["text_muted"]),
                self.normal_panel,
                self.roughness_panel,
                ft.Container(expand=True),
                self.progress_bar,
                ft.Row([self.btn_save], alignment="end"),
            ], spacing=SPACING["md"], expand=True),
            padding=SPACING["md"],
            width=320,
            bgcolor=COLORS["surface_alt"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
        )

        self.page.add(
            ft.Container(
                content=ft.Column([
                    header,
                    summary_bar,
                    ft.Row([
                        preview_container,
                        controls_container,
                    ], expand=True, spacing=SPACING["lg"]),
                ], expand=True),
                padding=SPACING["xl"],
                expand=True
            )
        )

    def on_mode_change(self, e):
        self.state.preview_mode = list(e.selection)[0]
        self.update_ui_state()
        self.update_preview()

    def on_param_change(self, _):
        self.state.normal_strength = float(self.sl_normal.value)
        self.state.normal_flip_g = self.chk_flip_g.value
        self.state.roughness_contrast = float(self.sl_rough.value)
        self.state.roughness_invert = self.chk_invert.value
        self.update_preview()

    def update_ui_state(self):
        self.normal_panel.visible = (self.state.preview_mode == "Normal")
        self.roughness_panel.visible = (self.state.preview_mode == "Roughness")
        
        if self.state.preview_mode == "Original":
            self.btn_save.disabled = True
            self.btn_save.content = ft.Text("Select Normal/Roughness to Save")
        else:
            self.btn_save.disabled = False
            self.btn_save.content = ft.Text(f"Save {self.state.preview_mode} Map(s)")
            
        self.page.update()

    def update_preview(self):
        if not self.original_img: return
        
        params = {
            'normal_strength': self.state.normal_strength,
            'normal_flip_g': self.state.normal_flip_g,
            'roughness_contrast': self.state.roughness_contrast,
            'roughness_invert': self.state.roughness_invert
        }
        
        norm, rough = self.service.generate_maps(self.original_img, params)
        
        target = self.original_img
        if self.state.preview_mode == "Normal": target = norm
        elif self.state.preview_mode == "Roughness": target = rough
        
        # Resize for preview performance
        display_img = target.copy()
        display_img.thumbnail((800, 800))
        
        img_bytes = self.service.get_preview_bytes(display_img)
        encoded = base64.b64encode(img_bytes).decode("ascii")
        self.img_preview.src = f"data:image/png;base64,{encoded}"
        self.page.update()

    def on_save_click(self, _):
        if self.state.is_processing: return
        
        self.state.is_processing = True
        self.btn_save.disabled = True
        self.progress_bar.visible = True
        self.page.update()

        params = {
            'normal_strength': self.state.normal_strength,
            'normal_flip_g': self.state.normal_flip_g,
            'roughness_contrast': self.state.roughness_contrast,
            'roughness_invert': self.state.roughness_invert
        }

        self.service.run_batch_save(
            files=self.state.files,
            params=params,
            mode=self.state.preview_mode,
            on_progress=self.handle_progress,
            on_complete=self.handle_complete
        )

    def handle_progress(self, progress, status):
        self.progress_bar.value = progress
        self.status_text.value = status
        self.page.update()

    def handle_complete(self, success_count, errors):
        self.state.is_processing = False
        self.btn_save.disabled = False
        self.progress_bar.visible = False
        
        if not errors:
            self.status_text.value = f"Successfully saved {success_count} {self.state.preview_mode} maps."
        else:
            self.status_text.value = f"Completed with {len(errors)} errors."
            
        self.page.update()

def start_app(targets: List[str]):
    app = SimplePbrFletApp(targets)
    ft.app(target=app.main)
