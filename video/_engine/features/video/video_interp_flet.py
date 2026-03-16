"""Video Frame Interpolation – Flet UI.

Compact two-column layout following the reference shell.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import List, Optional

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

from features.video.video_interp_service import VideoInterpService
from features.video.video_interp_state import VideoInterpState


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


def start_app(targets: List[str] | None = None):
    async def main(page: ft.Page):
        panel_height = 300
        state = VideoInterpState()
        service = VideoInterpService()

        if targets:
            video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
            valid = [Path(p) for p in targets if Path(p).exists() and Path(p).suffix.lower() in video_exts]
            if valid:
                state.input_path = valid[0]

        title = t("video_interp_gui.title") or "Frame Interpolation"
        configure_page(page, title, window_profile="form")
        page.bgcolor = COLORS["app_bg"]

        # ── controls ──
        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        preview_title = ft.Text("No video selected", size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"])
        preview_meta = ft.Text("Interpolation uses the first queued clip as the source preview.", size=11, color=COLORS["text_muted"])
        queue_badge = status_badge("1 file" if state.input_path else "0 files", "muted")
        method_badge = status_badge("mci", "accent")
        output_badge = status_badge("Interpolated", "muted")
        output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

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
            border_color=COLORS["line"],
            dense=True,
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
            border_color=COLORS["line"],
            dense=True,
        )

        def _sync_output_hint():
            if not state.input_path:
                output_hint.value = "Output path appears after a video is queued."
                return
            out_dir = state.input_path.parent / "Interpolated"
            mult = mult_dropdown.value or "2x"
            qual = quality_dropdown.value or "mci"
            output_hint.value = f"{out_dir}\\{state.input_path.stem}_{mult}_{qual}.mp4"

        def refresh_files():
            file_list.controls.clear()
            if state.input_path:
                preview_title.value = state.input_path.name
                preview_meta.value = "Target frame rate and interpolation method are applied to this clip."
                file_list.controls.append(_file_row(state.input_path))
            else:
                preview_title.value = "No video selected"
                preview_meta.value = "Launch from the context menu on a video file."
                file_list.controls.append(
                    ft.Container(
                        padding=SPACING["md"],
                        bgcolor=COLORS["surface_alt"],
                        border=ft.border.all(1, COLORS["line"]),
                        border_radius=RADII["sm"],
                        content=ft.Text(
                            "No video selected. Launch from the context menu on a video file.",
                            color=COLORS["text_muted"],
                        ),
                    )
                )

        def update_ui():
            progress_bar.visible = state.is_processing or state.progress > 0
            progress_bar.value = state.progress
            status_text.value = state.status_text or "Ready"
            start_btn.disabled = state.is_processing or not state.input_path
            cancel_btn.disabled = not state.is_processing
            open_output_btn.visible = state.last_output is not None

            queue_badge.content.value = "1 file" if state.input_path else "0 files"
            method_badge.content.value = quality_dropdown.value or "mci"
            _sync_output_hint()
            detail_text.value = output_hint.value
            page.update()

        def open_output_folder(_=None):
            if state.last_output and state.last_output.parent.exists():
                os.startfile(str(state.last_output.parent))
            elif state.input_path:
                d = state.input_path.parent / "Interpolated"
                if d.exists():
                    os.startfile(str(d))

        def open_result(_=None):
            if state.last_output and state.last_output.exists():
                os.startfile(str(state.last_output))

        def open_preview_source(_=None):
            if state.input_path and state.input_path.exists():
                os.startfile(str(state.input_path))

        def on_dropdown_change(_):
            update_ui()

        mult_dropdown.on_select = on_dropdown_change
        quality_dropdown.on_select = on_dropdown_change

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
                dialog = ft.AlertDialog(
                    title=ft.Text("Interpolation Complete"),
                    content=ft.Text(f"Output: {output_path.name}" if output_path else "Done"),
                    actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))],
                )
                page.open(dialog)

        def on_start(e):
            if not state.input_path or state.is_processing:
                return
            state.is_processing = True
            state.multiplier = mult_dropdown.value or "Target 30fps"
            state.quality_mode = quality_dropdown.value or "mci"
            update_ui()
            threading.Thread(
                target=service.interpolate,
                args=(state.input_path, state.multiplier, state.quality_mode, on_progress, on_complete),
                daemon=True,
            ).start()

        def on_cancel(e):
            service.cancel()
            state.status_text = "Cancelling..."
            update_ui()

        # ── buttons ──
        start_btn = apply_button_sizing(
            ft.ElevatedButton("Start Interpolation", on_click=on_start, bgcolor=COLORS["accent"], color=COLORS["text"]),
            "primary",
        )
        cancel_btn = icon_action_button(ft.Icons.CLOSE, tooltip="Cancel", on_click=on_cancel, disabled=True)
        open_output_btn = icon_action_button(ft.Icons.OPEN_IN_NEW, tooltip="Open output folder", on_click=open_output_folder)
        open_result_btn = icon_action_button(ft.Icons.PLAY_ARROW, tooltip="Play result", on_click=open_result, tone="success")
        preview_action = apply_button_sizing(ft.TextButton("Open Source", on_click=open_preview_source), "compact")

        refresh_files()

        # ── layout ──
        header = compact_meta_strip(
            title,
            description="Interpolate video frames using FFmpeg minterpolate filter.",
            badges=[queue_badge, method_badge, output_badge],
        )
        files_card = section_card(
            "Input Video",
            ft.Container(
                height=panel_height,
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
                        ft.Text("Queued Clip", size=11, color=COLORS["text_soft"]),
                        ft.Container(content=file_list, height=72),
                    ],
                    spacing=SPACING["sm"],
                ),
            ),
        )
        settings_card = section_card(
            "Interpolation Settings",
            ft.Container(
                height=panel_height,
                content=ft.Column(
                    [
                        mult_dropdown,
                        quality_dropdown,
                        ft.Divider(height=1, color=COLORS["line"]),
                        ft.Text(
                            "mci produces higher quality but is significantly slower.",
                            size=11,
                            color=COLORS["text_soft"],
                        ),
                        output_hint,
                        ft.Container(expand=True),
                        action_bar(
                            status=ft.Column([status_text, detail_text], spacing=2, tight=True),
                            progress=progress_bar,
                            primary=start_btn,
                            secondary=[open_output_btn, open_result_btn, cancel_btn],
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
