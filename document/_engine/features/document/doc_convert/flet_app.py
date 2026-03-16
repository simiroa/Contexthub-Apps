"""Document Converter – Flet UI.

Two-column layout following the audio_convert / video_convert reference shell.
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
    integrated_title_bar,
    section_card,
    status_badge,
)
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.window import reveal_desktop_window
from utils.i18n import t

from features.document.doc_convert.state import DocConvertState
from features.document.doc_convert.service import DocConvertService, get_common_formats


# ── helpers ──────────────────────────────────────────────────────────


def _file_row(src: Path) -> ft.Container:
    size_kb = f"{src.stat().st_size // 1024} KB" if src.exists() else ""
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Row(
            [
                ft.Icon("description", size=16, color=COLORS["text_muted"]),
                ft.Text(
                    src.name, size=12, color=COLORS["text"],
                    expand=True, no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(size_kb, size=10, color=COLORS["text_soft"]),
            ],
            spacing=SPACING["sm"],
        ),
    )


def _resolve_output_dir(state: DocConvertState) -> Path | None:
    if state.custom_output_dir:
        return state.custom_output_dir
    if not state.files:
        return None
    if state.use_subfolder:
        return state.files[0].parent / "Converted_Docs"
    return state.files[0].parent


def _output_summary(state: DocConvertState) -> str:
    if not state.files:
        return "Output path appears after files are queued."
    out_dir = _resolve_output_dir(state)
    sample = state.files[0].stem
    fmt_label = state.target_format or "?"
    # Show a representative output name
    return f"{out_dir}\\{sample} → {fmt_label}" if out_dir else "Output path unavailable."

# ── entry point ──────────────────────────────────────────────────────


def start_app(targets: List[str] | None = None):
    """Entry point called from main.py."""

    async def main(page: ft.Page):
        state = DocConvertState()
        service = DocConvertService()

        raw = [Path(p) for p in (targets or [])]
        state.files = list(dict.fromkeys(f for f in raw if f.exists()))
        capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        folder_picker = None

        configure_page(page, t("doc_convert.title"), window_profile="form")
        page.bgcolor = COLORS["app_bg"]
        if not capture_mode:
            folder_picker = ft.FilePicker()
            page.overlay.append(folder_picker)

        # detect formats
        state.available_formats = get_common_formats(state.files)
        if state.available_formats:
            state.target_format = state.available_formats[0]

        # ── controls ──
        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        queue_badge = status_badge("0 files", "muted")
        format_badge = status_badge(state.target_format or "—", "accent")
        output_badge = status_badge("Converted_Docs", "muted")
        output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        status_text = ft.Text(t("common.ready"), size=12, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(
            value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"],
        )

        # format dropdown
        format_options = (
            [ft.dropdown.Option(key=lbl, text=lbl) for lbl in state.available_formats]
            if state.available_formats
            else [ft.dropdown.Option(key="none", text=t("common.no_target"))]
        )

        dd_format = ft.Dropdown(
            label=t("doc_convert.target_format"),
            value=state.target_format or "none",
            options=format_options,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            expand=True,
        )

        # DPI dropdown (visible only for image targets)
        dd_dpi = ft.Dropdown(
            label="DPI",
            value="300",
            options=[ft.dropdown.Option(v) for v in ["72", "150", "200", "300", "400", "600"]],
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            width=110,
        )
        dpi_row = ft.Row(
            controls=[dd_dpi],
            spacing=SPACING["xs"],
            visible=False,
        )

        # output options
        subfolder_check = ft.Checkbox(
            label=t("doc_convert.create_subfolder"),
            value=state.use_subfolder,
            scale=0.95,
        )

        # ── refresh & sync ──

        def refresh_files():
            file_list.controls.clear()
            if state.files:
                for src in state.files:
                    file_list.controls.append(_file_row(src))
            else:
                file_list.controls.append(
                    ft.Container(
                        padding=SPACING["md"],
                        bgcolor=COLORS["surface_alt"],
                        border=ft.border.all(1, COLORS["line"]),
                        border_radius=RADII["sm"],
                        content=ft.Text(
                            "No document files yet. Launch from the context menu on one or more source files.",
                            color=COLORS["text_muted"],
                        ),
                    )
                )

        def sync_meta():
            queue_badge.content.value = f"{len(state.files)} files"
            format_badge.content.value = state.target_format or "—"
            if state.custom_output_dir:
                output_badge.content.value = "Custom folder"
            elif state.use_subfolder:
                output_badge.content.value = "Converted_Docs"
            else:
                output_badge.content.value = "Source folder"
            output_hint.value = _output_summary(state)
            detail_text.value = output_hint.value

        def open_output_folder(_=None):
            out_dir = _resolve_output_dir(state)
            if out_dir and out_dir.exists():
                os.startfile(str(out_dir))

        def use_source_folder(_=None):
            state.custom_output_dir = None
            state.use_subfolder = False
            subfolder_check.value = False
            update_ui()

        def choose_output_folder(_=None):
            if folder_picker is None:
                return
            selected_dir = folder_picker.get_directory_path(
                dialog_title="Choose Output Folder",
                initial_directory=str(state.custom_output_dir) if state.custom_output_dir else None,
            )
            if selected_dir:
                state.custom_output_dir = Path(selected_dir)
                state.use_subfolder = False
                subfolder_check.value = False
                update_ui()

        def update_ui():
            progress_bar.visible = state.is_processing or state.progress > 0
            progress_bar.value = state.progress
            status_text.value = state.status_text or t("common.ready")
            convert_btn.disabled = state.is_processing or not state.files or not state.target_format or state.target_format == "none"
            cancel_btn.disabled = not state.is_processing
            open_output_btn.disabled = _resolve_output_dir(state) is None
            sync_meta()
            page.update()

        # ── event handlers ──

        def on_format_select(e):
            state.target_format = dd_format.value or ""
            is_image = "Image" in state.target_format or "이미지" in state.target_format
            dpi_row.visible = is_image
            update_ui()

        def on_dpi_select(e):
            state.dpi = int(dd_dpi.value or "300")

        dd_format.on_select = on_format_select
        dd_dpi.on_select = on_dpi_select
        subfolder_check.on_change = lambda e: (
            setattr(state, "use_subfolder", bool(e.control.value)),
            setattr(state, "custom_output_dir", None if e.control.value else state.custom_output_dir),
            update_ui(),
        )

        def _run_convert():
            state.is_processing = True
            state.status_text = t("common.initializing")
            state.progress = 0.0
            page.run_thread(update_ui)

            def on_progress(idx, total, name):
                state.progress = idx / total if total else 0
                state.status_text = t("common.processing")
                state.detail_text = name
                page.run_thread(update_ui)

            try:
                options = {"dpi": state.dpi, "separate_pages": True}
                success, errors, last_dir = service.convert_files(
                    state.files,
                    state.target_format,
                    use_subfolder=state.use_subfolder,
                    custom_output_dir=state.custom_output_dir,
                    options=options,
                    on_progress=on_progress,
                )

                state.is_processing = False
                state.errors = errors
                state.last_converted = last_dir
                if errors:
                    state.status_text = t("common.completed_with_errors")
                    state.detail_text = f"{success} {t('common.success')}, {len(errors)} {t('common.error')}"
                else:
                    state.status_text = t("common.success_msg")
                    state.detail_text = t("common.files_converted", count=success)
                state.progress = 1.0
                page.run_thread(update_ui)

                message = f"Converted {success}/{success + len(errors)} files."
                if errors:
                    message += "\n\n" + "\n".join(errors[:5])
                dialog = ft.AlertDialog(
                    title=ft.Text("Document Conversion Complete"),
                    content=ft.Text(message),
                    actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))],
                )
                page.open(dialog)

            except Exception as exc:
                state.is_processing = False
                state.status_text = t("common.error")
                state.detail_text = str(exc)
                state.progress = 0.0
                page.run_thread(update_ui)

        def on_convert_click(e):
            if (
                state.is_processing
                or not state.files
                or not state.target_format
                or state.target_format == "none"
            ):
                return
            threading.Thread(target=_run_convert, daemon=True).start()

        def on_cancel_click(e):
            service.cancel()
            state.status_text = "Cancelling..."
            update_ui()

        # ── buttons ──
        convert_btn = apply_button_sizing(
            ft.ElevatedButton(
                "Convert Documents",
                on_click=on_convert_click,
                bgcolor=COLORS["accent"],
                color=COLORS["text"],
            ),
            "primary",
        )
        cancel_btn = apply_button_sizing(
            ft.OutlinedButton("Cancel", on_click=on_cancel_click, disabled=True),
            "compact",
        )
        open_output_btn = apply_button_sizing(
            ft.OutlinedButton("Open Output", on_click=open_output_folder),
            "compact",
        )
        source_folder_btn = apply_button_sizing(
            ft.OutlinedButton("Source Folder", on_click=use_source_folder),
            "compact",
        )
        choose_folder_btn = apply_button_sizing(
            ft.OutlinedButton("Choose Folder", on_click=choose_output_folder),
            "compact",
        )

        # ── initial state ──
        refresh_files()
        sync_meta()

        if not state.files:
            status_text.value = t("doc_convert.select_files")
            status_text.color = COLORS["warning"]
        elif not state.available_formats:
            status_text.value = t("common.no_target")
            status_text.color = COLORS["warning"]

        # ── layout ──
        header = compact_meta_strip(
            t("doc_convert.title"),
            badges=[queue_badge, format_badge, output_badge],
        )
        files_card = section_card("Input", ft.Container(content=file_list, height=240))
        settings_card = section_card(
            "Settings",
            ft.Column(
                [
                    dd_format,
                    dpi_row,
                    ft.Divider(height=1, color=COLORS["line"]),
                    subfolder_check,
                    output_hint,
                ],
                spacing=SPACING["sm"],
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
                        integrated_title_bar(page, t("doc_convert.title")),
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
                                            ft.Column([files_card], expand=3),
                                            ft.Column([settings_card], expand=2),
                                        ],
                                    ),
                                    action_bar(
                                        status=ft.Column(
                                            [status_text, detail_text],
                                            spacing=2,
                                            tight=True,
                                        ),
                                        progress=progress_bar,
                                        primary=convert_btn,
                                        secondary=[
                                            source_folder_btn,
                                            choose_folder_btn,
                                            open_output_btn,
                                            cancel_btn,
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
