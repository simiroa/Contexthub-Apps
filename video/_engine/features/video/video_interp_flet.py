import threading
from pathlib import Path
from typing import List, Optional

import flet as ft

from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.theme import configure_page
from utils.i18n import t

from features.video.video_interp_service import VideoInterpService
from features.video.video_interp_state import VideoInterpState

def start_app(targets: List[str] | None = None):
    def main(page: ft.Page):
        state = VideoInterpState()
        service = VideoInterpService()

        if targets and len(targets) > 0:
            state.input_path = Path(targets[0])

        configure_page(page, t("video_interp_gui.title"))
        page.window_width = 480
        page.window_height = 600

        # --- Components ---
        input_text = ft.Text(state.input_path.name if state.input_path else "No video selected", size=13, color=COLORS["text"], expand=True)
        
        input_card = ft.Container(
            content=ft.Row([
                ft.Icon("movie", color=COLORS["text_muted"], size=18),
                input_text
            ]),
            bgcolor=COLORS["surface"],
            padding=12,
            border_radius=RADII["sm"],
            border=ft.border.all(1, COLORS["line"]),
        )

        mult_dropdown = ft.Dropdown(
            label="Multiplier / Target",
            options=[
                ft.dropdown.Option("2x"),
                ft.dropdown.Option("4x"),
                ft.dropdown.Option("Target 30fps"),
                ft.dropdown.Option("Target 60fps"),
            ],
            value="Target 30fps",
            expand=True,
            bgcolor=COLORS["field_bg"],
        )

        quality_dropdown = ft.Dropdown(
            label="Method (mi_mode)",
            options=[
                ft.dropdown.Option("mci", text="mci (High Quality)"),
                ft.dropdown.Option("blend", text="blend (Fast)"),
            ],
            value="mci",
            expand=True,
            bgcolor=COLORS["field_bg"],
        )

        progress_bar = ft.ProgressBar(value=0, color=COLORS["accent"], bgcolor=COLORS["line"], height=10, border_radius=5)
        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])

        def on_play_result(e):
            if state.last_output and state.last_output.exists():
                import os
                os.startfile(str(state.last_output))

        btn_play = ft.ElevatedButton(
            content=ft.Row([ft.Icon("play_circle_filled", size=16), ft.Text("Open Result")], alignment="center"),
            bgcolor="#1E8449",
            on_click=on_play_result,
            visible=False,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
        )

        def update_ui():
            progress_bar.value = state.progress
            status_text.value = state.status_text
            btn_start.disabled = state.is_processing
            btn_play.visible = state.last_output is not None
            page.update()

        def on_progress(p, text):
            state.progress = p
            state.status_text = text
            page.run_thread(update_ui)

        def on_complete(success, output_path, error):
            state.is_processing = False
            state.progress = 1.0 if success else 0
            state.status_text = "Complete" if success else f"Error: {error}"
            state.last_output = output_path
            page.run_thread(update_ui)
            
            if success:
                page.open(ft.AlertDialog(title=ft.Text("Success"), content=ft.Text("Video interpolation finished.")))

        def on_start_click(e):
            if not state.input_path:
                return
            state.is_processing = True
            state.multiplier = mult_dropdown.value
            state.quality_mode = quality_dropdown.value
            update_ui()

            threading.Thread(target=service.interpolate, args=(
                state.input_path, state.multiplier, state.quality_mode, on_progress, on_complete
            ), daemon=True).start()

        btn_start = ft.ElevatedButton(
            content=ft.Text("Start Interpolation", weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            bgcolor=COLORS["accent"],
            height=48,
            expand=True,
            on_click=on_start_click,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
        )

        page.add(
            ft.Column([
                ft.Text(t("video_interp_gui.title"), size=20, weight="bold"),
                ft.Text("Input Video", size=12, color=COLORS["text_muted"]),
                input_card,
                ft.Row([mult_dropdown, quality_dropdown], spacing=10),
                ft.Divider(height=1, color=COLORS["line"]),
                ft.Column([
                    status_text,
                    progress_bar,
                ], spacing=4),
                btn_start,
                btn_play
            ], spacing=20, scroll=ft.ScrollMode.AUTO)
        )

    ft.app(target=main)
