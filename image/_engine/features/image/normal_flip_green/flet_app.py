import flet as ft
from pathlib import Path
from typing import List, Optional
import os

from .service import NormalFlipService
from .state import NormalFlipState
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import apply_desktop_window
from utils.i18n import t

class NormalFlipFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = NormalFlipService()
        self.state = NormalFlipState(files=[Path(f) for f in initial_files if Path(f).exists()])
        
        self.file_list = ft.Column(scroll="auto", expand=True)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.status_text = ft.Text(t("normal_flip.ready") or "Ready to flip", size=12, color=COLORS["text_muted"])
        self.btn_run = ft.ElevatedButton(
            t("normal_flip.run_btn") or "Flip Green Channel",
            icon="swap_vert",
            on_click=self.on_run_click,
            bgcolor=COLORS["accent"],
            color=COLORS["text"],
            height=50,
            expand=True,
        )
        apply_button_sizing(self.btn_run, "primary")

    def main(self, page: ft.Page):
        self.page = page
        title = t("normal_flip.header") or "Normal Map Flip G"
        configure_page(page, title, window_profile="compact")
        page.update()
        
        self.setup_ui()
        self.refresh_file_list()

    def setup_ui(self):
        header = ft.Container(
            content=ft.Column([
                ft.Text(t("normal_flip.header") or "Normal Map Flip G", size=24, weight="bold"),
                ft.Text(t("normal_flip.desc") or "Convert between DirectX and OpenGL normal maps.", size=14, color=COLORS["text_muted"]),
            ]),
            padding=ft.padding.only(bottom=SPACING["lg"])
        )

        info_card = ft.Container(
            content=ft.Column([
                ft.Text("작업 결과", weight="bold"),
                ft.Text("입력 파일과 같은 폴더에 `_flipped` 접미사 파일을 생성합니다.", size=12, color=COLORS["text_muted"]),
            ], spacing=4),
            padding=SPACING["md"],
            bgcolor=COLORS["surface_alt"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
        )

        file_container = ft.Container(
            content=self.file_list,
            height=150,
            padding=SPACING["md"],
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
        )

        self.page.add(
            ft.Container(
                content=ft.Column([
                    header,
                    info_card,
                    ft.Text(f"Target Files ({len(self.state.files)})", size=12, weight="bold", color=COLORS["text_muted"]),
                    file_container,
                    ft.Container(
                        content=action_bar(status=self.status_text, primary=self.btn_run, progress=self.progress_bar),
                        padding=ft.padding.only(top=SPACING["lg"])
                    )
                ], expand=True),
                padding=SPACING["xl"],
                expand=True
            )
        )

    def refresh_file_list(self):
        self.file_list.controls.clear()
        for f in self.state.files:
            self.file_list.controls.append(
                ft.Row(
                    [
                        ft.Icon("image_outlined", color=COLORS["text_muted"], size=16),
                        ft.Text(f.name, size=13, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ],
                    spacing=8,
                )
            )
        self.page.update()

    def on_run_click(self, _):
        if not self.state.files or self.state.is_processing: return
        
        self.state.is_processing = True
        self.btn_run.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.page.update()

        self.service.flip_green_batch(
            files=self.state.files,
            on_progress=self.handle_progress,
            on_complete=self.handle_complete
        )

    def handle_progress(self, progress, status):
        self.progress_bar.value = progress
        self.status_text.value = status
        self.page.update()

    def handle_complete(self, count, errors):
        self.state.is_processing = False
        self.btn_run.disabled = False
        self.progress_bar.visible = False
        
        if not errors:
            self.status_text.value = f"Successfully flipped {count} file(s)."
            self.show_success_dialog(count)
        else:
            self.status_text.value = f"Completed with {len(errors)} errors."
            self.show_error_dialog(errors)
            
        self.page.update()

    def show_success_dialog(self, count):
        def close_dlg(e):
            self.page.dialog.open = False
            self.page.update()
            if count > 0:
                self.page.window_close()

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Processing Complete"),
            content=ft.Text(f"Successfully flipped green channel for {count} images.\nOutput files have '_flipped' suffix."),
            actions=[ft.TextButton("OK", on_click=close_dlg)],
        )
        self.page.dialog.open = True

    def show_error_dialog(self, errors):
        error_msg = "\n".join(errors[:5])
        if len(errors) > 5:
            error_msg += f"\n...and {len(errors)-5} more."
            
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Errors Occurred"),
            content=ft.Text(error_msg),
            actions=[ft.TextButton("OK", on_click=lambda e: setattr(self.page.dialog, 'open', False))],
        )
        self.page.dialog.open = True

def start_app(targets: List[str]):
    app = NormalFlipFletApp(targets)
    ft.app(target=app.main)
