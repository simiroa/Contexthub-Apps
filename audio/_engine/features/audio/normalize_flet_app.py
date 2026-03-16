import os
import threading
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.layout import (
    action_bar,
    apply_button_sizing,
    compact_meta_strip,
    icon_action_button,
    integrated_title_bar,
    section_card,
    status_badge,
)
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.window import reveal_desktop_window
from utils.i18n import t

from features.audio.normalize_service import AudioNormalizeService
from features.audio.normalize_state import AudioNormalizeState


def _file_row(src: Path) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Row(
            [
                ft.Icon("audiotrack", size=16, color=COLORS["text_muted"]),
                ft.Text(src.name, size=12, color=COLORS["text"], expand=True, no_wrap=True),
                ft.Text(src.suffix.upper().lstrip("."), size=10, color=COLORS["text_soft"]),
            ],
            spacing=SPACING["sm"],
        ),
    )


def start_app(targets: List[str] | None = None):
    async def main(page: ft.Page):
        state = AudioNormalizeState()
        service = AudioNormalizeService()

        if targets:
            audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"}
            state.input_paths = [Path(path) for path in targets if Path(path).suffix.lower() in audio_exts]

        configure_page(page, t("audio_normalize_gui.title"), window_profile="form")
        page.bgcolor = COLORS["app_bg"]
        page.title = t("audio_normalize_gui.title")

        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        if state.input_paths:
            for path in state.input_paths:
                file_list.controls.append(_file_row(path))
        else:
            file_list.controls.append(
                ft.Container(
                    padding=SPACING["md"],
                    bgcolor=COLORS["surface_alt"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    content=ft.Text("No audio files yet. Launch from the context menu on one or more source files.", color=COLORS["text_muted"]),
                )
            )

        queue_badge = status_badge(f"{len(state.input_paths)} files", "muted")
        ffmpeg_badge = status_badge("FFmpeg ready" if service.ffmpeg else "FFmpeg missing", "success" if service.ffmpeg else "warning")

        target_slider = ft.Slider(
            min=-30,
            max=-5,
            divisions=25,
            label="{value}",
            value=state.target_loudness,
            on_change=lambda e: setattr(state, "target_loudness", e.control.value),
        )
        true_peak_slider = ft.Slider(
            min=-5,
            max=-0.1,
            divisions=49,
            label="{value}",
            value=state.true_peak,
            on_change=lambda e: setattr(state, "true_peak", e.control.value),
        )
        loudness_range_slider = ft.Slider(
            min=1,
            max=20,
            divisions=19,
            label="{value}",
            value=state.loudness_range,
            on_change=lambda e: setattr(state, "loudness_range", e.control.value),
        )

        status_text = ft.Text(t("common.ready"), size=12, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        play_btn = ft.ElevatedButton(
            content=ft.Row([ft.Icon("play_arrow", size=16), ft.Text("Play Last Result")], alignment="center"),
            bgcolor="#1E8449",
            visible=False,
            on_click=lambda e: on_play_last(e),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
        )
        open_btn = icon_action_button(ft.Icons.OPEN_IN_NEW, tooltip="Open output folder", disabled=True)

        def _open_output_path(_=None):
            if state.last_output_path and state.last_output_path.exists():
                os.startfile(str(state.last_output_path.parent))

        def on_play_last(e):
            if state.last_output_path and state.last_output_path.exists():
                os.startfile(str(state.last_output_path))

        def open_output_folder(_=None):
            _open_output_path()

        def update_ui():
            progress_bar.visible = state.is_processing or state.progress > 0
            progress_bar.value = state.progress
            status_text.value = state.status_text
            run_btn.disabled = state.is_processing or not state.input_paths or not service.ffmpeg
            cancel_btn.disabled = not state.is_processing
            open_btn.disabled = state.last_output_path is None
            play_btn.visible = state.last_output_path is not None
            ffmpeg_badge.content.value = "FFmpeg ready" if service.ffmpeg else "FFmpeg missing"
            detail_text.value = state.last_output_path.name if state.last_output_path else ""
            page.update()

        def on_progress(current, total, filename):
            state.progress = 0 if total == 0 else current / total
            state.status_text = f"Processing {current + 1}/{total}: {filename}"
            page.run_thread(update_ui)

        def on_complete(success, total, errors, last_path):
            state.is_processing = False
            state.progress = 1.0 if total else 0
            state.status_text = f"Complete: {success}/{total} success"
            state.last_output_path = last_path
            page.run_thread(update_ui)

            message = f"Normalized {success}/{total} files."
            if errors:
                message += "\n\n" + "\n".join(errors[:5])
            dialog = ft.AlertDialog(
                title=ft.Text("Normalization Complete"),
                content=ft.Text(message),
                actions=[
                    ft.TextButton("OK", on_click=lambda e: page.close(dialog)),
                ],
            )
            page.open(dialog)

        def on_run_click(e):
            if not state.input_paths or state.is_processing or not service.ffmpeg:
                return
            state.is_processing = True
            state.last_output_path = None
            state.status_text = "Starting..."
            state.progress = 0
            update_ui()
            threading.Thread(
                target=service.normalize_audio,
                args=(
                    state.input_paths,
                    state.target_loudness,
                    state.true_peak,
                    state.loudness_range,
                    on_progress,
                    on_complete,
                ),
                daemon=True,
            ).start()

        def on_cancel_click(e):
            service.cancel()
            state.status_text = "Cancelling..."
            update_ui()

        run_btn = apply_button_sizing(
            ft.ElevatedButton("Normalize", on_click=on_run_click, bgcolor=COLORS["accent"], color=COLORS["text"]),
            "primary",
        )
        cancel_btn = icon_action_button(ft.Icons.CLOSE, tooltip=t("common.cancel"), on_click=on_cancel_click, disabled=True)
        play_btn = icon_action_button(ft.Icons.PLAY_ARROW, tooltip="Play last result", on_click=on_play_last, disabled=False, tone="success")
        open_btn.on_click = open_output_folder

        file_list_card = section_card(
            "Files to Normalize",
            ft.Container(
                content=file_list,
                height=320,
            ),
        )
        settings_card = section_card(
            t("audio_normalize_gui.title"),
            ft.Container(
                height=320,
                content=ft.Column(
                    [
                        ft.Text(t("audio_normalize_gui.target_loudness"), size=12, weight="bold", color=COLORS["text"]),
                        target_slider,
                        ft.Text(t("audio_normalize_gui.true_peak"), size=12, weight="bold", color=COLORS["text"]),
                        true_peak_slider,
                        ft.Text("Loudness Range (LRA)", size=12, weight="bold", color=COLORS["text"]),
                        loudness_range_slider,
                        ffmpeg_badge,
                        ft.Container(expand=True),
                        action_bar(
                            status=ft.Column([status_text, detail_text], spacing=2, tight=True),
                            progress=progress_bar,
                            primary=run_btn,
                            secondary=[open_btn, play_btn, cancel_btn],
                            embedded=True,
                        ),
                    ],
                    expand=True,
                    spacing=SPACING["md"],
                ),
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
                        integrated_title_bar(page, t("audio_normalize_gui.title")),
                        ft.Container(
                            expand=True,
                            padding=ft.padding.all(SPACING["sm"]),
                            content=ft.Column(
                                expand=True,
                                spacing=SPACING["sm"],
                                controls=[
                                    compact_meta_strip(t("audio_normalize_gui.title"), badges=[queue_badge, ffmpeg_badge]),
                                    ft.Row(
                                        expand=True,
                                        spacing=SPACING["sm"],
                                        controls=[
                                            ft.Container(expand=True, content=file_list_card),
                                            ft.Container(width=404, content=settings_card),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            )
        )
        update_ui()
        await reveal_desktop_window(page)

    ft.run(main, view=ft.AppView.FLET_APP_HIDDEN)
