"""Audio Separator – Flet UI.

Shared by extract_bgm and extract_voice with parameterized title/description/mode.
Two-column layout following the reference shell.
"""

from __future__ import annotations

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
    media_preview_card,
    section_card,
    status_badge,
)
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.window import reveal_desktop_window
from utils.i18n import t

from features.audio.separate_service import AudioSeparateService
from features.audio.separate_state import AudioSeparateState


def _file_row(src: Path) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Row(
            [
                ft.Icon(ft.Icons.AUDIO_FILE, size=16, color=COLORS["text_muted"]),
                ft.Text(src.name, size=12, color=COLORS["text"], expand=True, no_wrap=True),
                ft.Text(src.suffix.upper().lstrip("."), size=10, color=COLORS["text_soft"]),
            ],
            spacing=SPACING["sm"],
        ),
    )


def start_app(
    targets: List[str] | None = None,
    *,
    title: str = "Audio Separator",
    description: str = "Split songs into stems or vocals/backing tracks.",
    initial_mode: str = "All Stems (4)",
):
    async def main(page: ft.Page):
        state = AudioSeparateState()
        service = AudioSeparateService()
        state.separation_mode = initial_mode

        if targets:
            audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"}
            state.input_paths = [Path(path) for path in targets if Path(path).suffix.lower() in audio_exts]

        configure_page(page, title, window_profile="form")
        page.bgcolor = COLORS["app_bg"]

        # ── controls ──
        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        preview_title = ft.Text("No audio files yet", size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"])
        preview_meta = ft.Text("The first selected file becomes the current separation preview target.", size=11, color=COLORS["text_muted"])
        queue_badge = status_badge(f"{len(state.input_paths)} files", "muted")
        model_badge = status_badge(state.model, "accent")
        output_badge = status_badge("Source folder", "muted")
        output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        model_dropdown = ft.Dropdown(
            label=t("audio_separate_gui.model"),
            options=[ft.dropdown.Option("htdemucs"), ft.dropdown.Option("htdemucs_ft"), ft.dropdown.Option("mdx_extra_q"), ft.dropdown.Option("hdemucs_mmi")],
            value=state.model,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            expand=True,
            dense=True,
        )
        format_dropdown = ft.Dropdown(
            label=t("audio_separate_gui.output_format"),
            options=[ft.dropdown.Option("wav"), ft.dropdown.Option("mp3"), ft.dropdown.Option("flac")],
            value=state.output_format,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            expand=True,
            dense=True,
        )
        mode_dropdown = ft.Dropdown(
            label=t("audio_separate_gui.separation_mode"),
            options=[ft.dropdown.Option("All Stems (4)"), ft.dropdown.Option("Vocals vs Backing (2)")],
            value=state.separation_mode,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            expand=True,
            dense=True,
        )

        open_btn = icon_action_button(ft.Icons.OPEN_IN_NEW, tooltip="Open output folder", disabled=True)

        def _sync_output_hint():
            if not state.input_paths:
                output_hint.value = "Output path appears after files are queued."
                return
            out_dir = state.custom_output_dir or state.last_output_dir or (state.input_paths[0].parent / "Separated_Audio")
            output_hint.value = f"{out_dir}\\"

        def refresh_files():
            file_list.controls.clear()
            if state.input_paths:
                preview_title.value = state.input_paths[0].name
                preview_meta.value = f"{len(state.input_paths)} queued | model {state.model}."
                for src in state.input_paths[:5]:
                    file_list.controls.append(_file_row(src))
            else:
                preview_title.value = "No audio files yet"
                preview_meta.value = "Launch from the context menu on one or more source files."
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

        def update_ui():
            progress_bar.visible = state.is_processing or state.progress > 0
            progress_bar.value = state.progress
            status_text.value = state.status_text
            run_btn.disabled = state.is_processing or not state.input_paths
            cancel_btn.disabled = not state.is_processing
            open_btn.disabled = (state.custom_output_dir or state.last_output_dir or (state.input_paths[0].parent / "Separated_Audio" if state.input_paths else None)) is None

            queue_badge.content.value = f"{len(state.input_paths)} files"
            model_badge.content.value = state.model
            if state.custom_output_dir:
                output_badge.content.value = "Custom folder"
            else:
                output_badge.content.value = "Source folder"
            _sync_output_hint()
            detail_text.value = output_hint.value
            page.update()

        def on_progress(current, total, filename):
            state.progress = 0 if total == 0 else current / total
            state.status_text = f"Processing {current + 1}/{total}: {filename}"
            page.run_thread(update_ui)

        def on_log(message: str):
            detail_text.value = message[:160]
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

        def on_run(e):
            if not state.input_paths or state.is_processing:
                return
            state.is_processing = True
            state.model = model_dropdown.value
            state.output_format = format_dropdown.value
            state.separation_mode = mode_dropdown.value
            state.last_output_dir = None
            detail_text.value = "Starting separation..."
            update_ui()
            threading.Thread(
                target=service.separate_audio,
                args=(state.input_paths, state.model, state.output_format, state.separation_mode, state.custom_output_dir, on_progress, on_complete, on_log),
                daemon=True,
            ).start()

        def on_cancel(e):
            service.cancel()
            state.status_text = "Cancelling..."
            update_ui()

        def open_output_folder(_=None):
            out_dir = state.custom_output_dir or state.last_output_dir
            if out_dir and out_dir.exists():
                os.startfile(str(out_dir))

        def open_preview_source(_=None):
            if state.input_paths and state.input_paths[0].exists():
                os.startfile(str(state.input_paths[0]))

        def use_source_folder(_=None):
            state.custom_output_dir = None
            update_ui()

        def use_default_separated_folder(_=None):
            if not state.input_paths:
                return
            state.custom_output_dir = state.input_paths[0].parent / "Separated_Audio"
            update_ui()

        open_btn.on_click = open_output_folder

        # ── buttons ──
        run_btn = apply_button_sizing(
            ft.ElevatedButton(t("audio_separate_gui.start_separation"), on_click=on_run, bgcolor=COLORS["accent"], color=COLORS["text"]),
            "primary",
        )
        cancel_btn = icon_action_button(ft.Icons.CLOSE, tooltip=t("common.cancel"), on_click=on_cancel, disabled=True)
        source_folder_btn = icon_action_button(ft.Icons.FOLDER_OPEN, tooltip="Use source folder", on_click=use_source_folder)
        converted_folder_btn = icon_action_button(ft.Icons.CREATE_NEW_FOLDER, tooltip="Use Separated_Audio folder", on_click=use_default_separated_folder)
        preview_action = apply_button_sizing(ft.TextButton("Play Source", on_click=open_preview_source), "compact")

        refresh_files()

        # ── layout ──
        header = compact_meta_strip(
            title,
            badges=[queue_badge, model_badge, output_badge],
        )
        files_card = section_card(
            "Input Files",
            ft.Container(
                height=340,
                content=ft.Column(
                    [
                        media_preview_card(
                            title=preview_title,
                            subtitle=preview_meta,
                            icon=ft.Icons.AUDIO_FILE,
                            accent=COLORS["surface"],
                            action=preview_action,
                            height=138,
                        ),
                        ft.Text("Recent Files", size=11, color=COLORS["text_soft"]),
                        ft.Container(content=file_list, height=112),
                    ],
                    spacing=SPACING["sm"],
                ),
            ),
        )
        settings_card = section_card(
            t("audio_separate_gui.extraction_settings"),
            ft.Container(
                height=340,
                content=ft.Column(
                    [
                        model_dropdown,
                        ft.Row([format_dropdown, mode_dropdown], spacing=SPACING["sm"]),
                        ft.Divider(height=1, color=COLORS["line"]),
                        output_hint,
                        ft.Container(expand=True),
                        action_bar(
                            status=ft.Column([status_text, detail_text], spacing=2, tight=True),
                            progress=progress_bar,
                            primary=run_btn,
                            secondary=[source_folder_btn, converted_folder_btn, open_btn, cancel_btn],
                            embedded=True,
                        ),
                    ],
                    expand=True,
                    spacing=SPACING["sm"],
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
                                            ft.Container(expand=True, content=files_card),
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
