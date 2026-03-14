from __future__ import annotations

import flet as ft

from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from utils.i18n import t

from .video_convert_service import VideoConvertService
from .video_convert_state import VideoConvertState


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


def create_video_convert_app(state: VideoConvertState):
    def video_convert_app(page: ft.Page):
        configure_page(page, t("video_convert_gui.title"), window_profile="form")
        page.bgcolor = COLORS["app_bg"]

        def update_ui(**kwargs):
            finished = kwargs.get("finished", False)
            success = kwargs.get("success", 0)
            total = kwargs.get("total", 0)
            errors = kwargs.get("errors") or []

            progress_bar.visible = state.is_processing or state.progress_value > 0
            progress_bar.value = state.progress_value
            status_text.value = state.status_text or "Ready"
            file_count_text.value = f"{len(state.files)} files queued"
            start_btn.disabled = state.is_processing or not state.files
            cancel_btn.text = t("common.cancel") if state.is_processing else t("common.close", "Close")
            custom_width_field.visible = state.scale == "Custom Width"
            crf_label.value = f"{t('video_convert_gui.quality_crf')}: {state.crf}"
            crf_slider.disabled = "H.264" not in state.output_format
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

        service = VideoConvertService(state, on_update=update_ui)
        formats = _format_options(state)
        if state.output_format not in formats:
            state.output_format = formats[0]

        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        for src in state.files:
            file_list.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
                    border_radius=RADII["sm"],
                    bgcolor=COLORS["surface"],
                    border=ft.border.all(1, COLORS["line"]),
                    content=ft.Row(
                        [ft.Icon(ft.Icons.MOVIE, size=16, color=COLORS["text_muted"]), ft.Text(src.name, size=12)],
                        spacing=SPACING["sm"],
                    ),
                )
            )
        if not file_list.controls:
            file_list.controls.append(
                ft.Container(
                    padding=SPACING["md"],
                    border_radius=RADII["sm"],
                    border=ft.border.all(1, COLORS["line"]),
                    bgcolor=COLORS["surface"],
                    content=ft.Text(
                        "No input videos yet. Launch from the context menu or pass video files to this app.",
                        color=COLORS["text_muted"],
                    ),
                )
            )

        file_count_text = ft.Text("", color=COLORS["text_muted"])
        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])
        crf_label = ft.Text("")

        fmt_dropdown = ft.Dropdown(
            label=t("video_convert_gui.format_label"),
            value=state.output_format,
            options=[ft.dropdown.Option(fmt) for fmt in formats],
            expand=True,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
        )
        scale_dropdown = ft.Dropdown(
            label=t("video_convert_gui.scale_label"),
            value=state.scale,
            options=[ft.dropdown.Option(s) for s in ["100%", "50%", "25%", "Custom Width"]],
            expand=True,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
        )
        custom_width_field = ft.TextField(
            label=t("video_convert_gui.width_placeholder"),
            value=state.custom_width,
            visible=state.scale == "Custom Width",
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
        )
        crf_slider = ft.Slider(min=0, max=51, divisions=51, value=state.crf)
        save_checkbox = ft.Checkbox(label=t("video_convert_gui.save_to_folder"), value=state.save_to_folder)
        delete_checkbox = ft.Checkbox(label=t("image_convert_gui.delete_original"), value=state.delete_original)

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

        fmt_dropdown.on_change = on_format_change
        scale_dropdown.on_change = on_scale_change
        custom_width_field.on_change = lambda e: setattr(state, "custom_width", e.control.value)
        crf_slider.on_change = lambda e: (setattr(state, "crf", int(e.control.value)), update_ui())
        save_checkbox.on_change = lambda e: setattr(state, "save_to_folder", bool(e.control.value))
        delete_checkbox.on_change = lambda e: setattr(state, "delete_original", bool(e.control.value))

        def start_conversion(e: ft.ControlEvent):
            service.start_conversion()

        def cancel_or_close(e: ft.ControlEvent):
            if state.is_processing:
                service.cancel_conversion()
            else:
                page.window_close()

        start_btn = ft.ElevatedButton(
            content=ft.Text(t("video_convert_gui.start_conversion")),
            on_click=start_conversion,
            bgcolor=COLORS["accent"],
            color=COLORS["text"],
        )
        cancel_btn = ft.OutlinedButton(content=ft.Text(t("common.cancel")), on_click=cancel_or_close)
        apply_button_sizing(start_btn, "primary")
        apply_button_sizing(cancel_btn, "compact")

        summary = ft.Container(
            padding=SPACING["lg"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[
                    ft.Text(t("video_convert_gui.title"), size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Convert source videos into delivery, proxy, mezzanine, or preview formats.",
                        color=COLORS["text_muted"],
                    ),
                    file_count_text,
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
                controls=[
                    ft.Text("Input Files", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(content=file_list, height=190),
                ],
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
                    ft.Row([fmt_dropdown, scale_dropdown], spacing=SPACING["sm"]),
                    custom_width_field,
                    ft.Column([crf_label, crf_slider], spacing=SPACING["xs"]),
                    ft.Text(t("video_convert_gui.quality_hint"), size=11, color=COLORS["text_muted"]),
                    save_checkbox,
                    delete_checkbox,
                ],
            ),
        )
        action = action_bar(status=status_text, progress=progress_bar, primary=start_btn, secondary=[cancel_btn])

        page.add(
            ft.Container(
                expand=True,
                padding=SPACING["lg"],
                bgcolor=COLORS["app_bg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["md"],
                    controls=[summary, files_card, settings_card, action],
                ),
            )
        )
        update_ui()

    return video_convert_app
