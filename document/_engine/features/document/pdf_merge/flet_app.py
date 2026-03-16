"""PDF Merge – Flet UI."""

from __future__ import annotations

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
from utils.files import get_safe_path
from utils.i18n import t

from features.document.pdf_merge.state import PdfMergeState
from features.document.pdf_merge.service import merge_pdfs


def _file_row(src: Path) -> ft.Container:
    size_kb = f"{src.stat().st_size // 1024} KB" if src.exists() else ""
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Row(
            [
                ft.Icon(ft.Icons.DESCRIPTION, size=16, color=COLORS["text_muted"]),
                ft.Text(src.name, size=12, color=COLORS["text"], expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(size_kb, size=10, color=COLORS["text_soft"]),
            ],
            spacing=SPACING["sm"],
        ),
    )


def start_app(targets: List[str] | None = None):
    """Entry point called from main.py."""

    async def main(page: ft.Page):
        state = PdfMergeState()
        state.files = list(dict.fromkeys(
            Path(p)
            for p in (targets or [])
            if Path(p).exists() and Path(p).suffix.lower() == ".pdf"
        ))
        configure_page(page, t("pdf_merge.title"), window_profile="compact")
        page.bgcolor = COLORS["app_bg"]

        file_list = ft.ListView(spacing=SPACING["xs"], auto_scroll=False)
        queue_badge = status_badge("0 files", "muted")
        output_badge = status_badge("Source folder", "muted")
        status_text = ft.Text(t("common.ready"), size=11, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=10, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(
            value=0,
            visible=False,
            color=COLORS["accent"],
            bgcolor=COLORS["line"],
            border_radius=4,
        )
        btn_merge = ft.ElevatedButton(
            t("pdf_merge.merge_btn"),
            on_click=None,
            bgcolor=COLORS["accent"],
            color=COLORS["text"],
        )
        btn_close = ft.OutlinedButton("Close", on_click=lambda _: page.window_close())
        apply_button_sizing(btn_merge, "primary")
        apply_button_sizing(btn_close, "compact")

        def refresh_files():
            file_list.controls.clear()
            if not state.files:
                file_list.controls.append(
                    ft.Container(
                        padding=SPACING["md"],
                        bgcolor=COLORS["surface_alt"],
                        border=ft.border.all(1, COLORS["line"]),
                        border_radius=RADII["sm"],
                        content=ft.Text(
                            "No PDF files selected.",
                            color=COLORS["text_muted"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                    )
                )
                return
            for src in state.files:
                file_list.controls.append(_file_row(src))

        def _output_hint() -> str:
            if not state.files:
                return ""
            dest = get_safe_path(state.files[0].parent / "merged.pdf")
            return str(dest)

        def sync_meta():
            queue_badge.content.value = f"{len(state.files)} files"
            output_badge.content.value = "Source folder"
            detail_text.value = _output_hint()
            btn_merge.disabled = state.is_processing or len(state.files) < 2

        def update_ui():
            progress_bar.visible = state.is_processing
            progress_bar.value = state.progress
            status_text.value = state.status_text
            btn_merge.content = ft.Text(
                t("common.processing") if state.is_processing else t("pdf_merge.merge_btn"),
                color=COLORS["text"],
                weight=ft.FontWeight.BOLD,
            )
            sync_meta()
            page.update()

        def on_progress(idx: int, total: int, name: str):
            if total == 0:
                return
            state.progress = idx / total
            state.status_text = t("common.processing")
            state.detail_text = name
            state.status_text = state.status_text
            state.detail_text = state.detail_text
            page.run_thread(update_ui)

        def _run_merge():
            state.is_processing = True
            state.status_text = t("common.initializing")
            state.detail_text = _output_hint()
            state.progress = 0.0
            page.run_thread(update_ui)

            try:
                dest = get_safe_path(state.files[0].parent / "merged.pdf")
                merge_pdfs(state.files, dest, on_progress=on_progress)
                state.is_processing = False
                state.status_text = t("common.success_msg")
                state.detail_text = t(
                    "pdf_merge.success_fmt",
                    count=len(state.files),
                    dest=dest.name,
                )
                state.progress = 1.0
            except Exception as exc:
                state.is_processing = False
                state.status_text = t("common.error")
                state.detail_text = str(exc)
                state.progress = 0.0
            page.run_thread(update_ui)

        def on_merge_click(e):
            if state.is_processing or len(state.files) < 2:
                return
            threading.Thread(target=_run_merge, daemon=True).start()

        btn_merge.on_click = on_merge_click

        # initial state
        if len(state.files) < 2:
            status_text.value = t("pdf_merge.select_min_2")
            status_text.color = COLORS["warning"]

        refresh_files()
        sync_meta()

        header = compact_meta_strip(
            f"🔗 {t('pdf_merge.title')}",
            description=t("pdf_merge.header"),
            badges=[queue_badge, output_badge],
        )
        files_card = section_card(
            "Input files",
            ft.Container(
                content=file_list,
                height=190,
            ),
        )
        settings_card = section_card(
            "Settings",
            ft.Column(
                [
                    ft.Text(
                        f"Output: {get_safe_path(state.files[0].parent / 'merged.pdf').name}" if state.files else "Output: merged.pdf",
                        size=12,
                        color=COLORS["text_muted"],
                    ),
                ],
                spacing=SPACING["xs"],
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
                        integrated_title_bar(page, t("pdf_merge.title")),
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
                                        status=ft.Column([status_text, detail_text], spacing=2, tight=True),
                                        progress=progress_bar,
                                        primary=btn_merge,
                                        secondary=[btn_close],
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
