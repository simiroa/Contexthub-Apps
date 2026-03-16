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

from .video_convert_service import VideoConvertService
from .video_convert_state import VideoConvertState


VIDEO_PRESETS = {
    "Web MP4": {"format_hint": "MP4 (H.264 High)", "scale": "100%", "crf": 20},
    "Edit Proxy": {"format_hint": "MP4 (H.264 Low/Proxy)", "scale": "50%", "crf": 28},
    "Master ProRes 422": {"format_hint": "MOV (ProRes 422)", "scale": "100%", "crf": 18},
    "Archive Copy": {"format_hint": "MKV (Copy Stream)", "scale": "100%", "crf": 18},
    "Animated GIF": {"format_hint": "GIF (High Quality)", "scale": "50%", "crf": 18},
}


def _format_options(state: VideoConvertState) -> list[str]:
    options: list[str] = []
    if state.has_nvenc:
        options.append("MP4 (H.264 NVENC)")
    options.extend(
        [
            "MP4 (H.264 High)",
            "MP4 (H.264 Low/Proxy)",
            "MOV (ProRes 422)",
            "MOV (ProRes 4444)",
            "MOV (DNxHD)",
            "MKV (Copy Stream)",
            "GIF (High Quality)",
        ]
    )
    return options


def _file_row(src: Path) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        border_radius=RADII["sm"],
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.MOVIE, size=16, color=COLORS["text_muted"]),
                ft.Text(src.name, size=12, color=COLORS["text"], expand=True, no_wrap=True),
                ft.Text(src.suffix.upper().lstrip("."), size=10, color=COLORS["text_soft"]),
            ],
            spacing=SPACING["sm"],
        ),
    )


def _resolve_output_dir(state: VideoConvertState) -> Path | None:
    if state.custom_output_dir:
        return state.custom_output_dir
    if not state.files:
        return None
    if state.save_to_folder:
        return state.files[0].parent / "Converted"
    return state.files[0].parent


def _output_summary(state: VideoConvertState) -> str:
    if not state.files:
        return "Output path appears after videos are queued."
    src = state.files[0]
    suffix = src.suffix
    if "MP4" in state.output_format:
        suffix = ".mp4"
    elif "MOV" in state.output_format:
        suffix = ".mov"
    elif "MKV" in state.output_format:
        suffix = ".mkv"
    elif "GIF" in state.output_format:
        suffix = ".gif"
    out_dir = _resolve_output_dir(state)
    name = f"{src.stem}{suffix}" if (state.save_to_folder or state.custom_output_dir) else f"{src.stem}_conv{suffix}"
    return f"{out_dir}\\{name}" if out_dir else "Output path unavailable."


def create_video_convert_app(state: VideoConvertState):
    async def video_convert_app(page: ft.Page):
        panel_height = 430
        configure_page(page, t("video_convert_gui.title"), window_profile="form")
        page.bgcolor = COLORS["app_bg"]

        service = VideoConvertService(state)
        formats = _format_options(state)
        if state.output_format not in formats:
            state.output_format = formats[0]

        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        preview_title = ft.Text("No input videos yet", size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"])
        preview_meta = ft.Text("Select a video to preview the current target and output setup.", size=11, color=COLORS["text_muted"])
        queue_badge = status_badge("0 files", "muted")
        format_badge = status_badge(state.output_format, "accent")
        gpu_badge = status_badge("NVENC ready" if state.has_nvenc else "CPU encode", "success" if state.has_nvenc else "warning")
        output_badge = status_badge("Source folder", "muted")
        output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])
        crf_label = ft.Text("")

        preset_dropdown = ft.Dropdown(
            label="Preset",
            value="Web MP4",
            options=[ft.dropdown.Option(name) for name in VIDEO_PRESETS],
            expand=True,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
        )
        fmt_dropdown = ft.Dropdown(
            label=t("video_convert_gui.format_label"),
            value=state.output_format,
            options=[ft.dropdown.Option(fmt) for fmt in formats],
            expand=True,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
        )
        scale_dropdown = ft.Dropdown(
            label=t("video_convert_gui.scale_label"),
            value=state.scale,
            options=[ft.dropdown.Option(s) for s in ["100%", "50%", "25%", "Custom Width"]],
            expand=True,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
        )
        custom_width_field = ft.TextField(
            label=t("video_convert_gui.width_placeholder"),
            value=state.custom_width,
            visible=state.scale == "Custom Width",
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
        )
        crf_slider = ft.Slider(min=0, max=51, divisions=51, value=state.crf)
        converted_folder_check = ft.Checkbox(label="Use Converted folder", value=state.save_to_folder, scale=0.95)
        delete_checkbox = ft.Checkbox(label=t("video_convert_gui.delete_original", "Delete original"), value=state.delete_original, scale=0.95)

        def refresh_files():
            file_list.controls.clear()
            if state.files:
                preview_title.value = state.files[0].name
                preview_meta.value = f"{len(state.files)} queued | first output follows current preset and format."
                for src in state.files[:5]:
                    file_list.controls.append(_file_row(src))
            else:
                preview_title.value = "No input videos yet"
                preview_meta.value = "Launch from the context menu or pass video files to this app."
                file_list.controls.append(
                    ft.Container(
                        padding=SPACING["md"],
                        border_radius=RADII["sm"],
                        border=ft.border.all(1, COLORS["line"]),
                        bgcolor=COLORS["surface_alt"],
                        content=ft.Text("No input videos yet. Launch from the context menu or pass video files to this app.", color=COLORS["text_muted"]),
                    )
                )

        def sync_meta():
            queue_badge.content.value = f"{len(state.files)} files"
            format_badge.content.value = state.output_format
            if state.custom_output_dir:
                output_badge.content.value = "Custom folder"
            elif state.save_to_folder:
                output_badge.content.value = "Converted"
            else:
                output_badge.content.value = "Source folder"
            crf_label.value = f"{t('video_convert_gui.quality_crf')}: {state.crf}"
            output_hint.value = _output_summary(state)
            detail_text.value = output_hint.value

        def open_output_folder(_=None):
            out_dir = _resolve_output_dir(state)
            if out_dir and out_dir.exists():
                os.startfile(str(out_dir))

        def open_preview_source(_=None):
            if state.files and state.files[0].exists():
                os.startfile(str(state.files[0]))

        def use_source_folder(_=None):
            state.custom_output_dir = None
            state.save_to_folder = False
            converted_folder_check.value = False
            update_ui()

        def use_converted_folder(_=None):
            if not state.files:
                return
            state.custom_output_dir = state.files[0].parent / "Converted"
            state.save_to_folder = True
            converted_folder_check.value = True
            update_ui()

        def apply_preset(name: str):
            preset = VIDEO_PRESETS[name]
            target = preset["format_hint"]
            if target == "MP4 (H.264 High)" and state.has_nvenc:
                target = "MP4 (H.264 NVENC)"
            state.output_format = target
            state.scale = preset["scale"]
            state.crf = preset["crf"]
            fmt_dropdown.value = state.output_format
            scale_dropdown.value = state.scale
            crf_slider.value = state.crf
            custom_width_field.visible = state.scale == "Custom Width"
            update_ui()

        def update_ui(**kwargs):
            finished = kwargs.get("finished", False)
            success = kwargs.get("success", 0)
            total = kwargs.get("total", 0)
            errors = kwargs.get("errors") or []

            progress_bar.visible = state.is_processing or state.progress_value > 0
            progress_bar.value = state.progress_value
            status_text.value = state.status_text or "Ready"
            start_btn.disabled = state.is_processing or not state.files
            cancel_btn.disabled = not state.is_processing
            open_output_btn.disabled = _resolve_output_dir(state) is None
            custom_width_field.visible = state.scale == "Custom Width"
            crf_slider.disabled = "H.264" not in state.output_format and "NVENC" not in state.output_format
            sync_meta()
            page.update()

            if finished:
                title = t("common.success") if not errors else t("common.error")
                message = f"Converted {success}/{total} files."
                if errors:
                    message += "\n\n" + "\n".join(errors[:5])
                dialog = ft.AlertDialog(
                    title=ft.Text(title),
                    content=ft.Text(message),
                    actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))],
                )
                page.open(dialog)

        service.on_update = update_ui

        def on_format_change(e: ft.ControlEvent):
            state.output_format = e.control.value
            if "High" in state.output_format:
                state.crf = 18
            elif "Low" in state.output_format:
                state.crf = 28
            crf_slider.value = state.crf
            update_ui()

        def on_scale_change(e: ft.ControlEvent):
            state.scale = e.control.value
            update_ui()

        preset_dropdown.on_select = lambda e: apply_preset(e.control.value)
        fmt_dropdown.on_select = on_format_change
        scale_dropdown.on_select = on_scale_change
        custom_width_field.on_change = lambda e: setattr(state, "custom_width", e.control.value)
        crf_slider.on_change = lambda e: (setattr(state, "crf", int(e.control.value)), update_ui())
        converted_folder_check.on_change = lambda e: (setattr(state, "save_to_folder", bool(e.control.value)), setattr(state, "custom_output_dir", None if e.control.value else state.custom_output_dir), update_ui())
        delete_checkbox.on_change = lambda e: setattr(state, "delete_original", bool(e.control.value))

        def start_conversion(e: ft.ControlEvent):
            service.start_conversion()

        def cancel_conversion(e: ft.ControlEvent):
            service.cancel_conversion()

        start_btn = apply_button_sizing(ft.ElevatedButton("Convert Video", on_click=start_conversion, bgcolor=COLORS["accent"], color=COLORS["text"]), "primary")
        cancel_btn = icon_action_button(ft.Icons.CLOSE, tooltip="Cancel", on_click=cancel_conversion, disabled=True)
        open_output_btn = icon_action_button(ft.Icons.OPEN_IN_NEW, tooltip="Open output folder", on_click=open_output_folder, disabled=True)
        source_folder_btn = icon_action_button(ft.Icons.FOLDER_OPEN, tooltip="Use source folder", on_click=use_source_folder)
        converted_folder_btn = icon_action_button(ft.Icons.CREATE_NEW_FOLDER, tooltip="Use Converted folder", on_click=use_converted_folder)
        preview_action = apply_button_sizing(ft.TextButton("Open Source", on_click=open_preview_source), "compact")

        refresh_files()
        sync_meta()

        header = compact_meta_strip(
            t("video_convert_gui.title"),
            badges=[queue_badge, format_badge, gpu_badge, output_badge],
        )
        files_card = section_card(
            "Input",
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
                height=panel_height,
                content=ft.Column(
                    [
                        preset_dropdown,
                        fmt_dropdown,
                        scale_dropdown,
                        custom_width_field,
                        ft.Column([crf_label, crf_slider], spacing=4),
                        ft.Row([converted_folder_check, delete_checkbox], wrap=True, spacing=SPACING["sm"], run_spacing=SPACING["xs"]),
                        output_hint,
                        ft.Container(expand=True),
                        action_bar(
                            status=ft.Column([status_text, detail_text], spacing=2, tight=True),
                            progress=progress_bar,
                            primary=start_btn,
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
                        integrated_title_bar(page, t("video_convert_gui.title")),
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

    return video_convert_app
