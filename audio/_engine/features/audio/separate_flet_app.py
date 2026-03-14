from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from utils.i18n import t

from features.audio.separate_service import AudioSeparateService
from features.audio.separate_state import AudioSeparateState


def start_app(
    targets: List[str] | None = None,
    *,
    title: str = "Audio Separator",
    description: str = "Split songs into stems or vocals/backing tracks.",
    initial_mode: str = "All Stems (4)",
):
    def main(page: ft.Page):
        state = AudioSeparateState()
        service = AudioSeparateService()
        state.separation_mode = initial_mode

        if targets:
            audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"}
            state.input_paths = [Path(path) for path in targets if Path(path).suffix.lower() in audio_exts]

        configure_page(page, title, window_profile="form")
        page.bgcolor = COLORS["app_bg"]

        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        for src in state.input_paths:
            file_list.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
                    bgcolor=COLORS["surface_alt"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    content=ft.Row(
                        [ft.Icon(ft.Icons.AUDIO_FILE, size=16, color=COLORS["text_muted"]), ft.Text(src.name, size=12)],
                        spacing=SPACING["sm"],
                    ),
                )
            )
        if not file_list.controls:
            file_list.controls.append(
                ft.Container(
                    padding=SPACING["md"],
                    bgcolor=COLORS["surface_alt"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    content=ft.Text(
                        "No audio files yet. Launch from the context menu on one or more source files.",
                        color=COLORS["text_muted"],
                    ),
                )
            )

        model_dropdown = ft.Dropdown(
            label=t("audio_separate_gui.model"),
            options=[ft.dropdown.Option("htdemucs"), ft.dropdown.Option("htdemucs_ft"), ft.dropdown.Option("mdx_extra_q"), ft.dropdown.Option("hdemucs_mmi")],
            value=state.model,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            expand=True,
        )
        format_dropdown = ft.Dropdown(
            label=t("audio_separate_gui.output_format"),
            options=[ft.dropdown.Option("wav"), ft.dropdown.Option("mp3"), ft.dropdown.Option("flac")],
            value=state.output_format,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            expand=True,
        )
        mode_dropdown = ft.Dropdown(
            label=t("audio_separate_gui.separation_mode"),
            options=[ft.dropdown.Option("All Stems (4)"), ft.dropdown.Option("Vocals vs Backing (2)")],
            value=state.separation_mode,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            expand=True,
        )

        log_lines = ft.Column(spacing=4, scroll=ft.ScrollMode.ADAPTIVE)
        if not log_lines.controls:
            log_lines.controls.append(ft.Text("Logs will appear here after the task starts.", color=COLORS["text_muted"], size=12))

        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])
        open_btn = ft.OutlinedButton(
            content=ft.Text(t("common.open_folder")),
            visible=False,
            on_click=lambda e: os.startfile(str(state.last_output_dir)) if state.last_output_dir and state.last_output_dir.exists() else None,
        )

        def update_ui():
            progress_bar.visible = state.is_processing or state.progress > 0
            progress_bar.value = state.progress
            status_text.value = state.status_text
            run_btn.disabled = state.is_processing or not state.input_paths
            cancel_btn.disabled = not state.is_processing
            open_btn.visible = state.last_output_dir is not None
            page.update()

        def on_progress(current, total, filename):
            state.progress = 0 if total == 0 else current / total
            state.status_text = f"Processing {current + 1}/{total}: {filename}"
            page.run_thread(update_ui)

        def on_log(message: str):
            if len(log_lines.controls) == 1 and isinstance(log_lines.controls[0], ft.Text) and log_lines.controls[0].value.startswith("Logs will"):
                log_lines.controls = []
            log_lines.controls.append(ft.Text(message, size=11, font_family="Consolas", color=COLORS["text_muted"]))
            if len(log_lines.controls) > 120:
                log_lines.controls = log_lines.controls[-120:]
            page.run_thread(page.update)

        def on_complete(success, total, errors, last_dir):
            state.is_processing = False
            state.progress = 1.0 if total else 0
            state.status_text = f"Complete: {success}/{total} success"
            state.last_output_dir = last_dir
            page.run_thread(update_ui)

            message = f"Processed {success}/{total} files."
            if errors:
                message += "\n\n" + "\n".join(errors[:5])
            dialog = ft.AlertDialog(
                title=ft.Text("Audio Separation Complete"),
                content=ft.Text(message),
                actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))],
            )
            page.open(dialog)

        def on_run(e: ft.ControlEvent):
            if not state.input_paths:
                return
            state.is_processing = True
            state.model = model_dropdown.value
            state.output_format = format_dropdown.value
            state.separation_mode = mode_dropdown.value
            state.last_output_dir = None
            log_lines.controls = [ft.Text("Starting separation...", size=11, font_family="Consolas", color=COLORS["text_muted"])]
            update_ui()
            threading.Thread(
                target=service.separate_audio,
                args=(state.input_paths, state.model, state.output_format, state.separation_mode, on_progress, on_complete, on_log),
                daemon=True,
            ).start()

        def on_cancel(e: ft.ControlEvent):
            service.cancel()
            state.status_text = "Cancelling..."
            update_ui()

        summary = ft.Container(
            padding=SPACING["lg"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[
                    ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(description, color=COLORS["text_muted"]),
                    ft.Text(f"{len(state.input_paths)} files queued", color=COLORS["text_muted"]),
                ],
            ),
        )

        files_card = ft.Container(
            padding=SPACING["md"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[ft.Text("Input Files", size=16, weight=ft.FontWeight.BOLD), ft.Container(content=file_list, height=150)],
            ),
        )
        settings_card = ft.Container(
            padding=SPACING["md"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            content=ft.Column(
                spacing=SPACING["md"],
                controls=[
                    ft.Text(t("audio_separate_gui.extraction_settings"), size=16, weight=ft.FontWeight.BOLD),
                    model_dropdown,
                    ft.Row([format_dropdown, mode_dropdown], spacing=SPACING["sm"]),
                ],
            ),
        )
        logs_card = ft.Container(
            padding=SPACING["md"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[ft.Text("Execution Log", size=16, weight=ft.FontWeight.BOLD), ft.Container(content=log_lines, height=170)],
            ),
        )

        run_btn = ft.ElevatedButton(content=ft.Text(t("audio_separate_gui.start_separation")), on_click=on_run, bgcolor=COLORS["accent"], color=COLORS["text"])
        cancel_btn = ft.OutlinedButton(content=ft.Text(t("common.cancel")), on_click=on_cancel, disabled=True)
        apply_button_sizing(run_btn, "primary")
        apply_button_sizing(cancel_btn, "compact")
        apply_button_sizing(open_btn, "compact")

        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                padding=SPACING["lg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["md"],
                    controls=[
                        summary,
                        files_card,
                        settings_card,
                        logs_card,
                        action_bar(status=status_text, progress=progress_bar, primary=run_btn, secondary=[cancel_btn, open_btn]),
                    ],
                ),
            )
        )
        update_ui()

    ft.app(target=main)
