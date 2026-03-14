import threading
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.theme import configure_page
from utils.i18n import t

from features.audio.normalize_service import AudioNormalizeService
from features.audio.normalize_state import AudioNormalizeState

def _apply_window(page: ft.Page, title: str):
    configure_page(page, title)
    page.window_width = 480
    page.window_height = 600
    page.window_min_width = 400
    page.window_min_height = 500

def start_app(targets: List[str] | None = None):
    def main(page: ft.Page):
        state = AudioNormalizeState()
        service = AudioNormalizeService()

        if targets:
            audio_exts = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma'}
            state.input_paths = [Path(p) for p in targets if Path(p).suffix.lower() in audio_exts]

        _apply_window(page, t("audio_normalize_gui.title"))

        # ── UI Components ──

        # File List
        file_list_col = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row([
                        ft.Icon("audiotrack", size=16, color=COLORS["text_muted"]),
                        ft.Text(p.name, size=12, color=COLORS["text"], expand=True),
                    ]),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=COLORS["surface"],
                    border_radius=RADII["sm"],
                    border=ft.border.all(1, COLORS["line"]),
                    tooltip=str(p)
                ) for p in state.input_paths
            ],
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
        )

        file_list_container = ft.Container(
            content=file_list_col,
            height=250,
            padding=8,
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            bgcolor=COLORS["field_bg"],
        )

        # Options
        target_loudness_slider = ft.Slider(
            min=-30, max=-5, divisions=25,
            label="{value} LUFS",
            value=state.target_loudness,
            on_change=lambda e: setattr(state, 'target_loudness', e.control.value)
        )
        
        true_peak_slider = ft.Slider(
            min=-5, max=-0.1, divisions=49,
            label="{value} dBTP",
            value=state.true_peak,
            on_change=lambda e: setattr(state, 'true_peak', e.control.value)
        )

        # Progress
        progress_bar = ft.ProgressBar(
            value=0,
            color=COLORS["accent"],
            bgcolor=COLORS["line"],
            height=10,
            border_radius=5,
        )
        status_text = ft.Text(t("common.ready"), size=12, color=COLORS["text_muted"])

        # ── Handlers ──
        def on_play_last(e):
            if state.last_output_path and state.last_output_path.exists():
                import os
                os.startfile(str(state.last_output_path))

        btn_play = ft.ElevatedButton(
            content=ft.Row([ft.Icon("play_arrow", size=16), ft.Text("Play Last Result")], alignment="center"),
            bgcolor="#1E8449",
            visible=False,
            on_click=on_play_last,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
        )

        def update_ui():
            progress_bar.value = state.progress
            status_text.value = state.status_text
            btn_run.disabled = state.is_processing
            btn_cancel.disabled = not state.is_processing
            btn_play.visible = state.last_output_path is not None
            page.update()

        def on_progress(current, total, filename):
            state.progress = current / total
            state.status_text = f"Processing {current+1}/{total}: {filename}"
            page.run_thread(update_ui)

        def on_complete(success, total, errors, last_path):
            state.is_processing = False
            state.progress = 1.0
            state.status_text = f"Complete: {success}/{total} success"
            state.last_output_path = last_path
            
            page.run_thread(update_ui)
            
            msg = f"Normalized {success}/{total} files."
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors[:5])
                page.open(ft.AlertDialog(title=ft.Text("Complete with warnings"), content=ft.Text(msg)))
            else:
                page.open(ft.AlertDialog(title=ft.Text("Success"), content=ft.Text(msg)))

        def on_run_click(e):
            if not state.input_paths:
                return
            
            state.is_processing = True
            state.last_output_path = None
            
            update_ui()
            
            threading.Thread(
                target=service.normalize_audio,
                args=(
                    state.input_paths,
                    state.target_loudness,
                    state.true_peak,
                    state.loudness_range,
                    on_progress,
                    on_complete
                ),
                daemon=True
            ).start()

        def on_cancel_click(e):
            service.cancel()
            state.status_text = "Cancelling..."
            update_ui()

        # Buttons
        btn_run = ft.ElevatedButton(
            content=ft.Text(t("audio_normalize_gui.normalize"), weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            bgcolor=COLORS["accent"],
            height=48,
            expand=True,
            on_click=on_run_click,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
        )

        btn_cancel = ft.ElevatedButton(
            content=ft.Text(t("common.cancel"), color=COLORS["text_muted"]),
            bgcolor=COLORS["surface"],
            height=48,
            expand=True,
            on_click=on_cancel_click,
            disabled=True,
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, COLORS["line"]),
                shape=ft.RoundedRectangleBorder(radius=RADII["sm"])
            ),
        )

        # ── Tabs ──
        
        main_tab = ft.Column([
            ft.Text("Files to Normalize", size=14, weight="bold"),
            file_list_container,
        ], spacing=10, expand=True)

        settings_tab = ft.Column([
            ft.Text("Normalization Settings", size=14, weight="bold"),
            ft.Container(
                content=ft.Column([
                    ft.Text(t("audio_normalize_gui.target_loudness"), size=12, weight="bold"),
                    target_loudness_slider,
                    ft.Text(t("audio_normalize_gui.true_peak"), size=12, weight="bold"),
                    true_peak_slider,
                ], spacing=15),
                padding=15,
                bgcolor=COLORS["surface"],
                border=ft.border.all(1, COLORS["line"]),
                border_radius=RADII["md"],
            )
        ], spacing=10, expand=True)

        tabs = ft.Tabs(
            length=2,
            selected_index=0,
            content=ft.Column([
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Normalize"),
                        ft.Tab(label="Settings"),
                    ],
                    indicator_color=COLORS["accent"],
                    label_color=COLORS["text"],
                    unselected_label_color=COLORS["text_muted"],
                ),
                ft.TabBarView(
                    controls=[
                        ft.Container(content=main_tab, padding=10),
                        ft.Container(content=settings_tab, padding=10),
                    ],
                    expand=True,
                )
            ], expand=True, spacing=0),
            expand=True,
        )

        # ── Layout ──
        page.add(
            ft.Column([
                ft.Text(t("audio_normalize_gui.title") + f" ({len(state.input_paths)})", size=20, weight="bold"),
                tabs,
                ft.Column([
                    status_text,
                    progress_bar,
                ], spacing=4),
                ft.Row([btn_cancel, btn_run], spacing=10),
                btn_play,
            ], spacing=15, expand=True)
        )

    ft.app(target=main)
