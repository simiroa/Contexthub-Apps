"""Video Audio Tools – Flet UI (extract or remove audio).

Shared by extract_audio and remove_audio with mode parameter.
Two-column layout following the reference shell.
"""

from __future__ import annotations

import os
from pathlib import Path

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

from .video_audio_state import VideoAudioState
from .video_audio_service import VideoAudioService


TITLES = {
    "extract": "Extract Audio",
    "remove": "Remove Audio",
    "separate": "Separate Voice/BGM",
}


def _file_row(src: Path) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Row(
            [
                ft.Icon(ft.Icons.MOVIE, size=16, color=COLORS["text_muted"]),
                ft.Text(src.name, size=12, color=COLORS["text"], expand=True, no_wrap=True),
                ft.Text(src.suffix.upper().lstrip("."), size=10, color=COLORS["text_soft"]),
            ],
            spacing=SPACING["sm"],
        ),
    )


def create_video_audio_app(state: VideoAudioState):
    """Return a Flet page builder for the video-audio tool."""

    async def video_audio_app(page: ft.Page):
        title = TITLES.get(state.mode, "Video Audio Tools")
        configure_page(page, title, window_profile="form")
        page.bgcolor = COLORS["app_bg"]

        service = VideoAudioService(state)
        custom_output_dir: list[Path | None] = [None]  # mutable closure cell

        # ── controls ──
        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        preview_title = ft.Text("No video files yet", size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"])
        preview_meta = ft.Text("The first selected video becomes the current preview target.", size=11, color=COLORS["text_muted"])
        queue_badge = status_badge(f"{len(state.files)} files", "muted")
        mode_badge = status_badge(state.mode.capitalize(), "accent")
        output_badge = status_badge("Audio_Output" if state.save_to_folder else "Source folder", "muted")
        output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        # extract options
        format_group = ft.RadioGroup(
            value=state.extract_format,
            content=ft.Row(
                [ft.Radio(value="MP3", label="MP3 (Compressed)"), ft.Radio(value="WAV", label="WAV (Lossless)")],
                spacing=SPACING["md"],
            ),
        )

        # separate options
        sep_group = ft.RadioGroup(
            value=state.separate_mode,
            content=ft.Row(
                [ft.Radio(value="Voice", label="Extract Voice"), ft.Radio(value="BGM", label="Extract BGM")],
                spacing=SPACING["md"],
            ),
        )

        subfolder_check = ft.Checkbox(label="Save to new folder", value=state.save_to_folder, scale=0.95)

        # ── helpers ──

        def _sync_output_hint():
            if not state.files:
                output_hint.value = "Output path appears after files are queued."
                return
            src = state.files[0]
            if custom_output_dir[0]:
                out_dir = custom_output_dir[0]
            elif state.save_to_folder:
                out_dir = src.parent / "Audio_Output"
            else:
                out_dir = src.parent

            if state.mode == "extract":
                ext = state.extract_format.lower()
                output_hint.value = f"{out_dir}\\{src.stem}.{ext}"
            elif state.mode == "remove":
                output_hint.value = f"{out_dir}\\{src.stem}_no_audio{src.suffix}"
            else:
                label = state.separate_mode.lower()
                output_hint.value = f"{out_dir}\\{src.stem}_{label}.wav"

        def refresh_files():
            file_list.controls.clear()
            if state.files:
                preview_title.value = state.files[0].name
                preview_meta.value = f"{len(state.files)} queued | current mode: {state.mode.capitalize()}."
                for f in state.files[:5]:
                    file_list.controls.append(_file_row(f))
            else:
                preview_title.value = "No video files yet"
                preview_meta.value = "Launch from the context menu."
                file_list.controls.append(
                    ft.Container(
                        padding=SPACING["md"],
                        bgcolor=COLORS["surface_alt"],
                        border=ft.border.all(1, COLORS["line"]),
                        border_radius=RADII["sm"],
                        content=ft.Text("No video files yet. Launch from the context menu.", color=COLORS["text_muted"]),
                    )
                )

        def update_ui(finished=False, success=0, total=0, errors=None):
            progress_bar.visible = state.is_processing or state.progress_value > 0
            progress_bar.value = state.progress_value
            status_text.value = state.status_text or "Ready"
            start_btn.disabled = state.is_processing or not state.files
            cancel_btn.disabled = not state.is_processing

            queue_badge.content.value = f"{len(state.files)} files"
            mode_badge.content.value = state.mode.capitalize()
            if custom_output_dir[0]:
                output_badge.content.value = "Custom folder"
            elif state.save_to_folder:
                output_badge.content.value = "Audio_Output"
            else:
                output_badge.content.value = "Source folder"
            _sync_output_hint()
            detail_text.value = output_hint.value
            page.update()

            if finished:
                msg = f"Processed {success}/{total} files."
                if errors:
                    msg += "\n\n" + "\n".join(errors[:5])
                dialog = ft.AlertDialog(
                    title=ft.Text(t("common.success") if not errors else t("common.error")),
                    content=ft.Text(msg),
                    actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))],
                )
                page.open(dialog)

        service.on_update = update_ui

        # ── event handlers ──
        format_group.on_change = lambda e: (setattr(state, "extract_format", e.data), update_ui())
        sep_group.on_change = lambda e: (setattr(state, "separate_mode", e.data), update_ui())
        subfolder_check.on_change = lambda e: (setattr(state, "save_to_folder", bool(e.control.value)), update_ui())

        def open_output_folder(_=None):
            if not state.files:
                return
            if custom_output_dir[0] and custom_output_dir[0].exists():
                os.startfile(str(custom_output_dir[0]))
            elif state.save_to_folder:
                d = state.files[0].parent / "Audio_Output"
                if d.exists():
                    os.startfile(str(d))
            else:
                os.startfile(str(state.files[0].parent))

        def open_preview_source(_=None):
            if state.files and state.files[0].exists():
                os.startfile(str(state.files[0]))

        def use_source_folder(_=None):
            custom_output_dir[0] = None
            state.save_to_folder = False
            subfolder_check.value = False
            update_ui()

        def use_output_folder(_=None):
            if not state.files:
                return
            custom_output_dir[0] = state.files[0].parent / "Audio_Output"
            state.save_to_folder = True
            subfolder_check.value = True
            update_ui()

        def on_start(e):
            service.start_processing()

        def on_cancel(e):
            service.cancel_processing()

        # ── buttons ──
        start_btn = apply_button_sizing(
            ft.ElevatedButton(f"{state.mode.capitalize()} Audio", on_click=on_start, bgcolor=COLORS["accent"], color=COLORS["text"]),
            "primary",
        )
        cancel_btn = icon_action_button(ft.Icons.CLOSE, tooltip="Cancel", on_click=on_cancel, disabled=True)
        open_output_btn = icon_action_button(ft.Icons.OPEN_IN_NEW, tooltip="Open output folder", on_click=open_output_folder)
        source_folder_btn = icon_action_button(ft.Icons.FOLDER_OPEN, tooltip="Use source folder", on_click=use_source_folder)
        output_folder_btn = icon_action_button(ft.Icons.CREATE_NEW_FOLDER, tooltip="Use Audio_Output folder", on_click=use_output_folder)
        preview_action = apply_button_sizing(ft.TextButton("Open Source", on_click=open_preview_source), "compact")

        refresh_files()

        # ── build mode-specific settings ──
        if state.mode == "extract":
            mode_options = ft.Column(
                [ft.Text("Output Format", size=13, color=COLORS["text_muted"]), format_group],
                spacing=SPACING["sm"],
            )
        elif state.mode == "remove":
            mode_options = ft.Column(
                [
                    ft.Text("Remove audio track from video files", color=COLORS["text_muted"]),
                    ft.Text("Video codec will be copied (fast)", size=11, color=COLORS["text_soft"]),
                ],
                spacing=SPACING["sm"],
            )
        else:
            mode_options = ft.Column(
                [ft.Text("Separation Target", size=13, color=COLORS["text_muted"]), sep_group],
                spacing=SPACING["sm"],
            )

        # ── layout ──
        header = compact_meta_strip(
            title,
            description=f"{title} from video files with output path control.",
            badges=[queue_badge, mode_badge, output_badge],
        )
        files_card = section_card(
            "Input Videos",
            ft.Container(
                height=320,
                content=ft.Column(
                    [
                        media_preview_card(
                            title=preview_title,
                            subtitle=preview_meta,
                            icon=ft.Icons.MOVIE,
                            accent=COLORS["surface"],
                            action=preview_action,
                            height=138,
                        ),
                        ft.Text("Recent Files", size=11, color=COLORS["text_soft"]),
                        ft.Container(content=file_list, height=92),
                    ],
                    spacing=SPACING["sm"],
                ),
            ),
        )
        settings_card = section_card(
            "Settings",
            ft.Container(
                height=320,
                content=ft.Column(
                    [
                        mode_options,
                        ft.Divider(height=1, color=COLORS["line"]),
                        subfolder_check,
                        output_hint,
                        ft.Container(expand=True),
                        action_bar(
                            status=ft.Column([status_text, detail_text], spacing=2, tight=True),
                            progress=progress_bar,
                            primary=start_btn,
                            secondary=[source_folder_btn, output_folder_btn, open_output_btn, cancel_btn],
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

    return video_audio_app


def start_app(targets: list[str] | None = None, mode: str = "extract"):
    """Entry point for main.py wrappers (extract_audio, remove_audio)."""
    state = VideoAudioState(mode=mode)
    if targets:
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
        state.files = [Path(p) for p in targets if Path(p).exists() and Path(p).suffix.lower() in video_exts]
    app = create_video_audio_app(state)
    ft.run(app, view=ft.AppView.FLET_APP_HIDDEN)
