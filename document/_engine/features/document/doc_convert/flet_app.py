"""Document Converter – Flet UI."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.tokens import COLORS, SPACING, RADII, WINDOWS
from contexthub.ui.flet.theme import configure_page

from features.document.doc_convert.state import DocConvertState
from features.document.doc_convert.service import get_common_formats, convert_files
from utils.i18n import t


# ── helpers ──────────────────────────────────────────────────────────

def _apply_compact_window(page: ft.Page, title: str):
    configure_page(page, title)
    preset = WINDOWS["compact"]
    page.window_width = preset["width"]
    page.window_height = preset["height"] + 40  # slightly taller for options
    page.window_min_width = preset["min_width"]
    page.window_min_height = preset["min_height"]


def _build_file_list(files: List[Path]) -> ft.Column:
    items = []
    for f in files:
        items.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon("description", size=16, color=COLORS["text_muted"]),
                        ft.Text(
                            f.name, size=12, color=COLORS["text"],
                            expand=True, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            f"{f.stat().st_size // 1024} KB" if f.exists() else "",
                            size=10, color=COLORS["text_soft"],
                        ),
                    ],
                    spacing=SPACING["xs"],
                ),
                padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=4),
            )
        )
    return ft.Column(controls=items, spacing=2, scroll=ft.ScrollMode.AUTO, height=90)


# ── entry point ──────────────────────────────────────────────────────

def start_app(targets: List[str] | None = None):
    """Entry point called from main.py."""

    def main(page: ft.Page):
        state = DocConvertState()

        raw = [Path(p) for p in (targets or [])]
        state.files = list(dict.fromkeys(f for f in raw if f.exists()))

        _apply_compact_window(page, t("doc_convert.title"))

        # detect formats
        state.available_formats = get_common_formats(state.files)
        if state.available_formats:
            state.target_format = state.available_formats[0]

        # ── controls ──
        lbl_header = ft.Text(
            "📄 " + t("doc_convert.title"),
            size=18, weight=ft.FontWeight.BOLD, color=COLORS["text"],
        )
        lbl_count = ft.Text(
            t("doc_convert.files_count", count=len(state.files)),
            size=12, color=COLORS["text_muted"],
        )

        file_card = ft.Container(
            content=_build_file_list(state.files),
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
            padding=SPACING["xs"],
        )

        # format dropdown
        format_options = [
            ft.dropdown.Option(key=lbl, text=lbl) for lbl in state.available_formats
        ] if state.available_formats else [
            ft.dropdown.Option(key="none", text=t("common.no_target"))
        ]

        def on_format_select(e):
            state.target_format = dd_format.value or ""
            # show DPI row only for image formats
            dpi_row.visible = "Image" in state.target_format or "이미지" in state.target_format
            page.update()

        dd_format = ft.Dropdown(
            value=state.target_format or "none",
            options=format_options,
            on_select=on_format_select,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            color=COLORS["text"],
            border_radius=RADII["sm"],
            height=40,
            expand=True,
        )

        # DPI dropdown (visible only for image targets)
        dpi_options = [
            ft.dropdown.Option(key=v, text=v) for v in ["72", "150", "200", "300", "400", "600"]
        ]

        def on_dpi_select(e):
            state.dpi = int(dd_dpi.value or "300")

        dd_dpi = ft.Dropdown(
            value="300",
            options=dpi_options,
            on_select=on_dpi_select,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            color=COLORS["text"],
            border_radius=RADII["sm"],
            height=40,
            width=100,
        )

        dpi_row = ft.Row(
            controls=[ft.Text("DPI:", size=12, color=COLORS["text_muted"]), dd_dpi],
            spacing=SPACING["xs"],
            visible=False,
        )

        # subfolder checkbox
        def on_subfolder_change(e):
            state.use_subfolder = cb_subfolder.value or False

        cb_subfolder = ft.Checkbox(
            label=t("doc_convert.create_subfolder"),
            value=True,
            on_change=on_subfolder_change,
            active_color=COLORS["accent"],
            check_color=COLORS["text"],
        )

        # settings card
        settings_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                t("doc_convert.target_format"),
                                size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"],
                            ),
                            dd_format,
                        ],
                        spacing=SPACING["sm"],
                    ),
                    dpi_row,
                    ft.Divider(height=1, color=COLORS["line"]),
                    cb_subfolder,
                ],
                spacing=SPACING["xs"],
            ),
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
            padding=SPACING["md"],
        )

        # progress
        status_text = ft.Text(t("common.ready"), size=11, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=10, color=COLORS["text_soft"])
        progress_bar = ft.ProgressBar(
            value=0, height=8, color=COLORS["accent"], bgcolor=COLORS["line"],
            border_radius=4,
        )

        # ── handlers ──
        def _update_ui():
            status_text.value = state.status_text
            detail_text.value = state.detail_text
            progress_bar.value = state.progress
            btn_convert.disabled = state.is_processing
            btn_convert.content = ft.Text(
                t("common.processing") if state.is_processing else t("common.convert_all"),
                weight=ft.FontWeight.BOLD, color=COLORS["text"],
            )
            page.update()

        def _run_convert():
            state.is_processing = True
            state.status_text = t("common.initializing")
            state.progress = 0.0
            page.run_thread(_update_ui)

            def on_progress(idx, total, name):
                state.progress = idx / total if total else 0
                state.status_text = t("common.processing")
                state.detail_text = name
                page.run_thread(_update_ui)

            try:
                options = {"dpi": state.dpi, "separate_pages": True}
                success, errors = convert_files(
                    state.files,
                    state.target_format,
                    use_subfolder=state.use_subfolder,
                    options=options,
                    on_progress=on_progress,
                )

                state.is_processing = False
                state.errors = errors
                if errors:
                    state.status_text = t("common.completed_with_errors")
                    state.detail_text = f"{success} {t('common.success')}, {len(errors)} {t('common.error')}"
                else:
                    state.status_text = t("common.success_msg")
                    state.detail_text = t("common.files_converted", count=success)
                state.progress = 1.0
                page.run_thread(_update_ui)

            except Exception as exc:
                state.is_processing = False
                state.status_text = t("common.error")
                state.detail_text = str(exc)
                state.progress = 0.0
                page.run_thread(_update_ui)

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
            page.window_close()

        # ── buttons ──
        btn_cancel = ft.ElevatedButton(
            content=ft.Text(t("common.cancel"), color=COLORS["text_muted"]),
            bgcolor="transparent",
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, COLORS["line"]),
                shape=ft.RoundedRectangleBorder(radius=RADII["sm"]),
            ),
            height=36, on_click=on_cancel_click, expand=True,
        )
        btn_convert = ft.ElevatedButton(
            content=ft.Text(
                t("common.convert_all"),
                weight=ft.FontWeight.BOLD, color=COLORS["text"],
            ),
            bgcolor=COLORS["accent"],
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=RADII["sm"]),
            ),
            height=36, on_click=on_convert_click, expand=True,
            disabled=not state.available_formats,
        )

        if not state.files:
            status_text.value = t("doc_convert.select_files")
            status_text.color = COLORS["warning"]
        elif not state.available_formats:
            status_text.value = t("common.no_target")
            status_text.color = COLORS["warning"]

        # ── layout ──
        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                padding=SPACING["lg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["sm"],
                    controls=[
                        ft.Row(
                            controls=[lbl_header, lbl_count],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        file_card,
                        settings_card,
                        ft.Container(expand=True),
                        status_text,
                        progress_bar,
                        detail_text,
                        ft.Row(
                            controls=[btn_cancel, btn_convert],
                            spacing=SPACING["sm"],
                        ),
                    ],
                ),
            )
        )

    ft.app(target=main)
