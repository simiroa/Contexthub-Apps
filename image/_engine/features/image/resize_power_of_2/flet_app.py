import flet as ft
from pathlib import Path
from typing import List, Optional
import os
from PIL import Image

from .service import ResizePotService
from .state import ResizePotState
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import apply_desktop_window
from utils.i18n import t

class ResizePotFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = ResizePotService()
        self.state = ResizePotState(files=[Path(f) for f in initial_files if Path(f).exists()])
        
        self.current_img_size = (0, 0)
        if self.state.files:
            try:
                with Image.open(self.state.files[0]) as img:
                    self.current_img_size = img.size
            except: pass

        self.setup_controls()

    def setup_controls(self):
        self.file_list = ft.Column(scroll="auto", expand=True)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        self.info_text = ft.Text("Parameters info...", size=13, color=COLORS["text_muted"])
        
        self.dd_size = ft.Dropdown(
            label=t("image_resize_gui.target_resolution") or "Target Size",
            options=[ft.dropdown.Option(s) for s in ["512", "1024", "2048", "4096", "8192"]],
            value=self.state.target_size,
            on_select=self.on_param_change,
            width=150,
        )
        self.chk_square = ft.Checkbox(
            label=t("image_resize_gui.force_square") or "Force Square (Padding)",
            value=self.state.force_square,
            on_change=self.on_param_change
        )
        self.rg_mode = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="Standard", label="Standard (Lanczos)"),
                ft.Radio(value="AI", label="AI Upscale (Real-ESRGAN)"),
            ]),
            value=self.state.mode,
            on_change=self.on_param_change
        )
        self.chk_folder = ft.Checkbox(label="Save to subfolder", value=self.state.save_to_folder, on_change=self.on_param_change)
        self.chk_delete = ft.Checkbox(label="Delete originals", value=self.state.delete_original, on_change=self.on_param_change)
        
        self.btn_run = ft.ElevatedButton(
            "Resize to POT",
            icon="compress",
            on_click=self.on_run_click,
            bgcolor=COLORS["accent"],
            color=COLORS["text"],
            height=50,
            expand=True,
        )
        self.btn_add_images = apply_button_sizing(ft.ElevatedButton("Add Images", icon="add_photo_alternate", on_click=self.on_pick_files), "toolbar")
        self.btn_clear_list = ft.IconButton(ft.Icons.DELETE_SWEEP, on_click=self.on_clear_files, tooltip="Clear List")
        self.file_picker: Optional[ft.FilePicker] = None
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"


    def main(self, page: ft.Page):
        self.page = page
        title = t("image_resize_gui.title") or "POT Image Resize"
        configure_page(page, title, window_profile="two_pane")
        if not self.capture_mode:
            self.file_picker = ft.FilePicker()
            page.overlay.append(self.file_picker)
        page.update()
        
        self.setup_ui()
        self.refresh_file_list()
        self.update_recommendation()

    def setup_ui(self):
        header = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(t("image_resize_gui.title") or "POT Image Resize", size=24, weight="bold"),
                    ft.Text("Set a target size, review the recommendation, then run one resize batch.", size=12, color=COLORS["text_muted"]),
                ], expand=True),
                ft.ElevatedButton("Add Images", icon=ft.Icons.ADD_PHOTO_ALTERNATE, on_click=self.on_pick_files),
                self.btn_clear_list,
            ], alignment="spaceBetween"),
            padding=ft.padding.only(bottom=SPACING["md"])
        )

        summary_card = ft.Container(
            content=ft.Row([
                ft.Text(f"입력 파일 {len(self.state.files)}개", color=COLORS["text_muted"]),
                ft.VerticalDivider(width=16, color="transparent"),
                ft.Text(f"타깃 {self.state.target_size}px", color=COLORS["text_muted"]),
                ft.VerticalDivider(width=16, color="transparent"),
                self.status_text,
            ], wrap=True),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
        )

        file_section = ft.Container(
            content=ft.Column([
                ft.Text("입력 파일", weight="bold"),
                ft.Container(
                    content=self.file_list,
                    height=200,
                    padding=SPACING["sm"],
                    bgcolor=COLORS["surface"],
                    border_radius=RADII["md"],
                    border=ft.border.all(1, COLORS["line"]),
                ),
            ], spacing=SPACING["sm"]),
            expand=True,
        )

        params_section = ft.Container(
            content=ft.Column([
                ft.Text("설정", size=16, weight="bold"),
                ft.Row([self.dd_size, self.chk_square], alignment="spaceBetween", wrap=True),
                ft.Divider(color=COLORS["line"]),
                ft.Text("Resize Method", size=14, weight="bold"),
                self.rg_mode,
                ft.Container(self.info_text, padding=SPACING["sm"], bgcolor=COLORS["surface_alt"], border_radius=RADII["sm"]),
                ft.Row([self.chk_folder, self.chk_delete], alignment="start", spacing=30),
                ft.Container(expand=True),
                action_bar(status=self.status_text, primary=self.btn_run, progress=self.progress_bar),
            ], spacing=SPACING["md"]),
            padding=SPACING["md"],
            bgcolor=COLORS["surface_alt"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
            width=360,
        )

        self.page.add(
            ft.Container(
                content=ft.Column([
                    header,
                    summary_card,
                    ft.Row([
                        file_section,
                        params_section,
                    ], expand=True, spacing=SPACING["lg"]),
                ], expand=True),
                padding=SPACING["xl"],
                expand=True
            )
        )

    def refresh_file_list(self):
        self.file_list.controls.clear()
        if not self.state.files:
            self.file_list.controls.append(ft.Text("이미지를 추가하면 여기에 처리 대상이 표시됩니다.", color=COLORS["text_muted"]))
        for f in self.state.files:
            self.file_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=COLORS["text_muted"]),
                        ft.Text(f.name, size=13, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=8),
                    padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
                    border_radius=RADII["sm"],
                    bgcolor=COLORS["surface_alt"],
                )
            )
        self.btn_run.disabled = not bool(self.state.files) or self.state.is_processing
        self.page.update()

    def on_pick_files(self, _):
        if self.file_picker is not None:
            files = self.file_picker.pick_files(
                allow_multiple=True,
                file_type=ft.FilePickerFileType.IMAGE,
            )
            self._consume_files(files)

    def on_file_result(self, e):
        self._consume_files(getattr(e, "files", None))

    def _consume_files(self, files):
        if not files:
            return
        known = {str(path.resolve()) for path in self.state.files}
        added = False
        for file in files:
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
        self.refresh_file_list()
        self.update_recommendation()

    def on_clear_files(self, _):
        self.state.files.clear()
        self.current_img_size = (0, 0)
        self.refresh_file_list()
        self.update_recommendation()

    def on_param_change(self, _):
        self.state.target_size = self.dd_size.value
        self.state.force_square = self.chk_square.value
        self.state.mode = self.rg_mode.value
        self.state.save_to_folder = self.chk_folder.value
        self.state.delete_original = self.chk_delete.value
        self.update_recommendation()

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
                color = COLORS["success"]
        elif ratio < 0.8:
            msg += f"Downscale: {ratio:.1f}x"
        else:
            msg += "Size change is minimal."

        self.info_text.value = msg
        self.info_text.color = color
        self.page.update()

    def on_run_click(self, _):
        if self.state.is_processing: return
        
        self.state.is_processing = True
        self.btn_run.disabled = True
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
            on_complete=self.handle_complete
        )

    def handle_progress(self, progress, status):
        self.progress_bar.value = progress
        self.status_text.value = status
        self.page.update()

    def handle_complete(self, success_count, errors):
        self.state.is_processing = False
        self.btn_run.disabled = False
        self.progress_bar.visible = False
        
        if not errors:
            self.status_text.value = f"Successfully resized {success_count} images."
            self.show_dialog("Success", f"Processed {success_count} images successfully.")
        else:
            self.status_text.value = f"Completed with {len(errors)} errors."
            self.show_dialog("Completed with Errors", "\n".join(errors[:5]))
            
        self.page.update()

    def show_dialog(self, title, message):
        def close_dlg(e):
            self.page.dialog.open = False
            self.page.update()
            self.page.window_close()
            
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=close_dlg)],
        )
        self.page.dialog.open = True
        self.page.update()

def start_app(targets: List[str]):
    app = ResizePotFletApp(targets)
    ft.app(target=app.main)
