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

from features.audio.audio_convert.service import AudioConvertService
from features.audio.audio_convert.state import AudioConvertState


AUDIO_PRESETS = {
    "Delivery MP3": {"format": "MP3", "quality": "High"},
    "Archive WAV": {"format": "WAV", "quality": "High"},
    "Open OGG": {"format": "OGG", "quality": "Medium"},
    "Apple AAC": {"format": "M4A", "quality": "High"},
}


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


def _resolve_output_dir(state: AudioConvertState) -> Path | None:
    if state.custom_output_dir:
        return state.custom_output_dir
    if not state.input_paths:
        return None
    if state.save_to_new_folder:
        return state.input_paths[0].parent / "Converted_Audio"
    return state.input_paths[0].parent


def _output_summary(state: AudioConvertState) -> str:
    if not state.input_paths:
        return "Output path appears after files are queued."
    out_dir = _resolve_output_dir(state)
    suffix = state.output_format.lower()
    stem = state.input_paths[0].stem
    sample_name = f"{stem}.{suffix}" if (state.save_to_new_folder or state.custom_output_dir) else f"{stem}_conv.{suffix}"
    return f"{out_dir}\\{sample_name}" if out_dir else "Output path unavailable."


def start_app(targets: List[str] | None = None):
    async def main(page: ft.Page):
        state = AudioConvertState()
        service = AudioConvertService()

        if targets:
            audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".aiff"}
            state.input_paths = [Path(path) for path in targets if Path(path).suffix.lower() in audio_exts]

        configure_page(page, t("audio_convert_gui.title"), window_profile="form")
        page.bgcolor = COLORS["app_bg"]

        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        preview_title = ft.Text("No audio files yet", size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"])
        preview_meta = ft.Text("Select audio files to convert. The first file is used as the current preview target.", size=11, color=COLORS["text_muted"])
        queue_badge = status_badge("0 files", "muted")
        format_badge = status_badge(state.output_format, "accent")
        output_badge = status_badge("Source folder", "muted")
        ffmpeg_badge = status_badge("FFmpeg ready" if service.ffmpeg else "FFmpeg missing", "success" if service.ffmpeg else "warning")
        output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        preset_dropdown = ft.Dropdown(
            label="Preset",
            value="Delivery MP3",
            options=[ft.dropdown.Option(name) for name in AUDIO_PRESETS],
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            expand=True,
        )
        fmt_dropdown = ft.Dropdown(
            label=t("audio_convert_gui.format_label"),
            options=[ft.dropdown.Option("MP3"), ft.dropdown.Option("WAV"), ft.dropdown.Option("OGG"), ft.dropdown.Option("FLAC"), ft.dropdown.Option("M4A")],
            value=state.output_format,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            expand=True,
        )
        qual_dropdown = ft.Dropdown(
            label=t("audio_convert_gui.quality_label"),
            options=[ft.dropdown.Option("High"), ft.dropdown.Option("Medium"), ft.dropdown.Option("Low")],
            value=state.quality,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            expand=True,
        )
        meta_check = ft.Checkbox(label=t("audio_convert_gui.copy_metadata"), value=state.copy_metadata, scale=0.95)
        converted_folder_check = ft.Checkbox(label="Use Converted_Audio folder", value=state.save_to_new_folder, scale=0.95)
        delete_check = ft.Checkbox(label=t("audio_convert_gui.delete_original"), value=state.delete_original, scale=0.95)

        def refresh_files():
            file_list.controls.clear()
            if state.input_paths:
                preview_title.value = state.input_paths[0].name
                preview_meta.value = f"{len(state.input_paths)} queued | output follows the selected format and quality."
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
                        content=ft.Text("No audio files yet. Launch from the context menu on one or more source files.", color=COLORS["text_muted"]),
                    )
                )

        def sync_meta():
            queue_badge.content.value = f"{len(state.input_paths)} files"
            format_badge.content.value = state.output_format
            if state.custom_output_dir:
                output_badge.content.value = "Custom folder"
            elif state.save_to_new_folder:
                output_badge.content.value = "Converted_Audio"
            else:
                output_badge.content.value = "Source folder"
            output_hint.value = _output_summary(state)
            detail_text.value = output_hint.value

        def open_output_folder(_=None):
            out_dir = _resolve_output_dir(state)
            if out_dir and out_dir.exists():
                os.startfile(str(out_dir))

        def open_preview_source(_=None):
            if state.input_paths and state.input_paths[0].exists():
                os.startfile(str(state.input_paths[0]))

        def use_source_folder(_=None):
            state.custom_output_dir = None
            state.save_to_new_folder = False
            converted_folder_check.value = False
            update_ui()

        def use_converted_folder(_=None):
            state.save_to_new_folder = True
            state.custom_output_dir = None
            converted_folder_check.value = True
            update_ui()

        def update_ui():
            progress_bar.visible = state.is_processing or state.progress > 0
            progress_bar.value = state.progress
            status_text.value = state.status_text
            convert_btn.disabled = state.is_processing or not state.input_paths
            cancel_btn.disabled = not state.is_processing
            open_output_btn.disabled = _resolve_output_dir(state) is None
            sync_meta()
            page.update()

        def apply_preset(name: str):
            config = AUDIO_PRESETS[name]
            state.output_format = config["format"]
            state.quality = config["quality"]
            fmt_dropdown.value = state.output_format
            qual_dropdown.value = state.quality
            update_ui()

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
            state.save_to_new_folder = bool(converted_folder_check.value)
            state.delete_original = bool(delete_check.value)
            update_ui()
            threading.Thread(
                target=service.convert_audio,
                args=(
                    state.input_paths,
                    state.output_format,
                    state.quality,
                    state.copy_metadata,
                    state.save_to_new_folder,
                    state.custom_output_dir,
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

        preset_dropdown.on_select = lambda e: apply_preset(e.control.value)
        fmt_dropdown.on_select = lambda e: (setattr(state, "output_format", e.control.value), update_ui())
        qual_dropdown.on_select = lambda e: (setattr(state, "quality", e.control.value), update_ui())
        converted_folder_check.on_change = lambda e: (setattr(state, "save_to_new_folder", bool(e.control.value)), setattr(state, "custom_output_dir", None if e.control.value else state.custom_output_dir), update_ui())
        meta_check.on_change = lambda e: setattr(state, "copy_metadata", bool(e.control.value))
        delete_check.on_change = lambda e: setattr(state, "delete_original", bool(e.control.value))

        convert_btn = apply_button_sizing(ft.ElevatedButton("Convert Audio", on_click=on_convert, bgcolor=COLORS["accent"], color=COLORS["text"]), "primary")
        cancel_btn = icon_action_button(ft.Icons.CLOSE, tooltip="Cancel", on_click=on_cancel, disabled=True)
        open_output_btn = icon_action_button(ft.Icons.OPEN_IN_NEW, tooltip="Open output folder", on_click=open_output_folder, disabled=True)
        source_folder_btn = icon_action_button(ft.Icons.FOLDER_OPEN, tooltip="Use source folder", on_click=use_source_folder)
        converted_folder_btn = icon_action_button(ft.Icons.CREATE_NEW_FOLDER, tooltip="Use Converted_Audio folder", on_click=use_converted_folder)
        preview_action = apply_button_sizing(ft.TextButton("Play Source", on_click=open_preview_source), "compact")

        refresh_files()
        sync_meta()

        header = compact_meta_strip(
            t("audio_convert_gui.title"),
            badges=[queue_badge, format_badge, output_badge, ffmpeg_badge],
        )
        files_card = section_card(
            "Input",
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
            "Settings",
            ft.Container(
                height=340,
                content=ft.Column(
                    [
                        preset_dropdown,
                        ft.Row([fmt_dropdown, qual_dropdown], spacing=SPACING["sm"]),
                        ft.Row([converted_folder_check, meta_check, delete_check], wrap=True, spacing=SPACING["sm"], run_spacing=SPACING["xs"]),
                        output_hint,
                        ft.Container(expand=True),
                        action_bar(
                            status=ft.Column([status_text, detail_text], spacing=2, tight=True),
                            progress=progress_bar,
                            primary=convert_btn,
                            secondary=[source_folder_btn, converted_folder_btn, open_output_btn, cancel_btn],
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
                        integrated_title_bar(page, t("audio_convert_gui.title")),
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
