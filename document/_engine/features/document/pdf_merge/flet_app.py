"""PDF Merge – Flet UI."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.tokens import COLORS, SPACING, RADII, WINDOWS
from contexthub.ui.flet.theme import configure_page

from features.document.pdf_merge.state import PdfMergeState
from features.document.pdf_merge.service import merge_pdfs
from utils.i18n import t


def _apply_compact_window(page: ft.Page, title: str):
    """Apply compact window preset for document tools."""
    configure_page(page, title)
    preset = WINDOWS["compact"]
    page.window_width = preset["width"]
    page.window_height = preset["height"]
    page.window_min_width = preset["min_width"]
    page.window_min_height = preset["min_height"]


def _build_file_list(files: List[Path]) -> ft.Column:
    """Build a scrollable file list display."""
    items = []
    for f in files:
        items.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon("description", size=16, color=COLORS["text_muted"]),
                        ft.Text(
                            f.name,
                            size=12,
                            color=COLORS["text"],
                            expand=True,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            f"{f.stat().st_size // 1024} KB" if f.exists() else "",
                            size=10,
                            color=COLORS["text_soft"],
                        ),
                    ],
                    spacing=SPACING["xs"],
                ),
                padding=ft.padding.symmetric(
                    horizontal=SPACING["sm"], vertical=4
                ),
            )
        )
    return ft.Column(
        controls=items,
        spacing=2,
        scroll=ft.ScrollMode.AUTO,
        height=100,
    )


def start_app(targets: List[str] | None = None):
    """Entry point called from main.py."""

    def main(page: ft.Page):
        state = PdfMergeState()

        # ------ resolve files ------
        raw = [Path(p) for p in (targets or [])]
        state.files = list(dict.fromkeys(f for f in raw if f.exists() and f.suffix.lower() == ".pdf"))

        _apply_compact_window(page, t("pdf_merge.title"))

        # ------ controls ------
        lbl_header = ft.Text(
            "🔗 " + t("pdf_merge.header"),
            size=18,
            weight=ft.FontWeight.BOLD,
            color=COLORS["text"],
        )
        lbl_count = ft.Text(
            t("doc_convert.files_count", count=len(state.files)),
            size=12,
            color=COLORS["text_muted"],
        )

        file_list = _build_file_list(state.files)
        file_card = ft.Container(
            content=file_list,
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
            padding=SPACING["xs"],
        )

        status_text = ft.Text(t("common.ready"), size=11, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=10, color=COLORS["text_soft"])
        progress_bar = ft.ProgressBar(
            value=0, height=8, color=COLORS["accent"], bgcolor=COLORS["line"],
            border_radius=4,
        )

        # ------ handlers ------
        def _update_ui():
            status_text.value = state.status_text
            detail_text.value = state.detail_text
            progress_bar.value = state.progress
            btn_merge.disabled = state.is_processing
            btn_merge.content = ft.Text(
                t("common.processing") if state.is_processing else t("pdf_merge.merge_btn"),
                weight=ft.FontWeight.BOLD,
                color=COLORS["text"],
            )
            page.update()

        def _on_progress(idx: int, total: int, name: str):
            if total == 0:
                return
            state.progress = idx / total
            state.status_text = t("common.processing")
            state.detail_text = name
            page.run_thread(_update_ui)

        def _run_merge():
            state.is_processing = True
            state.status_text = t("common.initializing")
            state.progress = 0.0
            page.run_thread(_update_ui)

            try:
                from utils.files import get_safe_path

                dest = get_safe_path(state.files[0].parent / "merged.pdf")
                merge_pdfs(state.files, dest, on_progress=_on_progress)

                state.is_processing = False
                state.status_text = t("common.success_msg")
                state.detail_text = t(
                    "pdf_merge.success_fmt",
                    count=len(state.files),
                    dest=dest.name,
                )
                state.progress = 1.0
                page.run_thread(_update_ui)

            except Exception as exc:
                state.is_processing = False
                state.status_text = t("common.error")
                state.detail_text = str(exc)
                state.progress = 0.0
                page.run_thread(_update_ui)

        def on_merge_click(e):
            if state.is_processing or len(state.files) < 2:
                return
            threading.Thread(target=_run_merge, daemon=True).start()

        def on_cancel_click(e):
            page.window_close()

        # ------ buttons ------
        btn_cancel = ft.ElevatedButton(
            content=ft.Text(t("common.cancel"), color=COLORS["text_muted"]),
            bgcolor="transparent",
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, COLORS["line"]),
                shape=ft.RoundedRectangleBorder(radius=RADII["sm"]),
            ),
            height=36,
            on_click=on_cancel_click,
            expand=True,
        )
        btn_merge = ft.ElevatedButton(
            content=ft.Text(
                t("pdf_merge.merge_btn"),
                weight=ft.FontWeight.BOLD,
                color=COLORS["text"],
            ),
            bgcolor=COLORS["accent"],
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=RADII["sm"]),
            ),
            height=36,
            on_click=on_merge_click,
            expand=True,
            disabled=len(state.files) < 2,
        )

        # ------ warn if not enough files ------
        if len(state.files) < 2:
            status_text.value = t("pdf_merge.select_min_2")
            status_text.color = COLORS["warning"]

        # ------ layout ------
        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                padding=SPACING["lg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["sm"],
                    controls=[
                        # header
                        ft.Row(
                            controls=[lbl_header, lbl_count],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        # file list
                        file_card,
                        # progress section
                        ft.Container(expand=True),
                        status_text,
                        progress_bar,
                        detail_text,
                        # footer buttons
                        ft.Row(
                            controls=[btn_cancel, btn_merge],
                            spacing=SPACING["sm"],
                        ),
                    ],
                ),
            )
        )

    ft.app(target=main)
