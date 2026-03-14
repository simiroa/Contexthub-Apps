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

from features.audio.audio_convert.service import AudioConvertService
from features.audio.audio_convert.state import AudioConvertState


def start_app(targets: List[str] | None = None):
    def main(page: ft.Page):
        state = AudioConvertState()
        service = AudioConvertService()

        if targets:
            audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".aiff"}
            state.input_paths = [Path(path) for path in targets if Path(path).suffix.lower() in audio_exts]

        configure_page(page, t("audio_convert_gui.title"), window_profile="form")
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

        fmt_dropdown = ft.Dropdown(
            label=t("audio_convert_gui.format_label"),
            options=[ft.dropdown.Option("MP3"), ft.dropdown.Option("WAV"), ft.dropdown.Option("OGG"), ft.dropdown.Option("FLAC"), ft.dropdown.Option("M4A")],
            value=state.output_format,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            expand=True,
        )
        qual_dropdown = ft.Dropdown(
            label=t("audio_convert_gui.quality_label"),
            options=[ft.dropdown.Option("High"), ft.dropdown.Option("Medium"), ft.dropdown.Option("Low")],
            value=state.quality,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            expand=True,
        )
        meta_check = ft.Checkbox(label=t("audio_convert_gui.copy_metadata"), value=state.copy_metadata)
        folder_check = ft.Checkbox(label=t("audio_convert_gui.save_to_folder"), value=state.save_to_new_folder)
        delete_check = ft.Checkbox(label=t("audio_convert_gui.delete_original"), value=state.delete_original)

        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])
        play_btn = ft.OutlinedButton(
            content=ft.Text("Open Last Result"),
            visible=False,
            on_click=lambda e: os.startfile(str(state.last_converted)) if state.last_converted and state.last_converted.exists() else None,
        )

        def update_ui():
            progress_bar.visible = state.is_processing or state.progress > 0
            progress_bar.value = state.progress
            status_text.value = state.status_text
            convert_btn.disabled = state.is_processing or not state.input_paths
            cancel_btn.disabled = not state.is_processing
            play_btn.visible = state.last_converted is not None
            page.update()

        def on_progress(current, total, filename):
            state.progress = 0 if total == 0 else current / total
            state.status_text = f"Processing {current + 1}/{total}: {filename}"
            page.run_thread(update_ui)

        def on_complete(success, total, errors, last_path):
            state.is_processing = False
            state.progress = 1.0 if total else 0
            state.status_text = f"Complete: {success}/{total} success"
            state.last_converted = last_path
            page.run_thread(update_ui)

            message = f"Converted {success}/{total} files."
            if errors:
                message += "\n\n" + "\n".join(errors[:5])
            dialog = ft.AlertDialog(
                title=ft.Text("Audio Conversion Complete"),
                content=ft.Text(message),
                actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))],
            )
            page.open(dialog)

        def on_convert(e: ft.ControlEvent):
            if not state.input_paths:
                return
            state.is_processing = True
            state.output_format = fmt_dropdown.value
            state.quality = qual_dropdown.value
            state.copy_metadata = bool(meta_check.value)
            state.save_to_new_folder = bool(folder_check.value)
            state.delete_original = bool(delete_check.value)
            state.last_converted = None
            update_ui()
            threading.Thread(
                target=service.convert_audio,
                args=(
                    state.input_paths,
                    state.output_format,
                    state.quality,
                    state.copy_metadata,
                    state.save_to_new_folder,
                    state.delete_original,
                    on_progress,
                    on_complete,
                ),
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
                    ft.Text(t("audio_convert_gui.title"), size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("Convert source audio into delivery formats with simple quality presets.", color=COLORS["text_muted"]),
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
                controls=[ft.Text("Input Files", size=16, weight=ft.FontWeight.BOLD), ft.Container(content=file_list, height=160)],
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
                    ft.Text("Output Settings", size=16, weight=ft.FontWeight.BOLD),
                    ft.Row([fmt_dropdown, qual_dropdown], spacing=SPACING["sm"]),
                    meta_check,
                    folder_check,
                    delete_check,
                ],
            ),
        )

        convert_btn = ft.ElevatedButton(content=ft.Text(t("audio_convert_gui.convert")), on_click=on_convert, bgcolor=COLORS["accent"], color=COLORS["text"])
        cancel_btn = ft.OutlinedButton(content=ft.Text(t("common.cancel")), on_click=on_cancel, disabled=True)
        apply_button_sizing(convert_btn, "primary")
        apply_button_sizing(cancel_btn, "compact")
        apply_button_sizing(play_btn, "compact")

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
                        action_bar(status=status_text, progress=progress_bar, primary=convert_btn, secondary=[cancel_btn, play_btn]),
                    ],
                ),
            )
        )
        update_ui()

    ft.app(target=main)
