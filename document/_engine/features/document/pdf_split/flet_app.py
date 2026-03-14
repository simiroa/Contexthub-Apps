"""PDF Split – Flet UI."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.tokens import COLORS, SPACING, RADII, WINDOWS
from contexthub.ui.flet.theme import configure_page

from features.document.pdf_split.state import PdfSplitState
from features.document.pdf_split.service import split_to_pages, split_to_images
from utils.i18n import t


# ── helpers ──────────────────────────────────────────────────────────

def _apply_compact_window(page: ft.Page, title: str):
    configure_page(page, title)
    preset = WINDOWS["compact"]
    page.window_width = preset["width"]
    page.window_height = preset["height"]
    page.window_min_width = preset["min_width"]
    page.window_min_height = preset["min_height"]


def _build_file_list(files: List[Path]) -> ft.Column:
    items = []
    for f in files:
        items.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon("picture_as_pdf", size=16, color=COLORS["text_muted"]),
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
    return ft.Column(controls=items, spacing=2, scroll=ft.ScrollMode.AUTO, height=100)


# ── entry point ──────────────────────────────────────────────────────

MODE_MAP = {
    0: ("pdf", "PDF"),
    1: ("png", "PNG"),
    2: ("jpg", "JPEG"),
}


def start_app(targets: List[str] | None = None):
    """Entry point called from main.py."""

    def main(page: ft.Page):
        state = PdfSplitState()

        raw = [Path(p) for p in (targets or [])]
        state.files = list(dict.fromkeys(
            f for f in raw if f.exists() and f.suffix.lower() == ".pdf"
        ))

        _apply_compact_window(page, t("pdf_split.split_title"))

        # ── controls ──
        lbl_header = ft.Text(
            "✂️ " + t("pdf_split.split_title"),
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

        # mode dropdown
        mode_options = [
            ft.dropdown.Option(key="pdf", text=t("pdf_split.mode_pdf")),
            ft.dropdown.Option(key="png", text=t("pdf_split.mode_png")),
            ft.dropdown.Option(key="jpg", text=t("pdf_split.mode_jpg")),
        ]

        def on_mode_select(e):
            state.mode = dd_mode.value or "pdf"
            dpi_row.visible = state.mode in ("png", "jpg")
            page.update()

        dd_mode = ft.Dropdown(
            value="pdf",
            options=mode_options,
            on_select=on_mode_select,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            color=COLORS["text"],
            border_radius=RADII["sm"],
            height=40,
            expand=True,
        )

        # DPI dropdown (hidden by default)
        dpi_options = [
            ft.dropdown.Option(key=v, text=v) for v in ["72", "150", "300", "600"]
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
            controls=[
                ft.Text("DPI:", size=12, color=COLORS["text_muted"]),
                dd_dpi,
            ],
            spacing=SPACING["xs"],
            visible=False,
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
                            dd_mode,
                        ],
                        spacing=SPACING["sm"],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    dpi_row,
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
            btn_split.disabled = state.is_processing
            btn_split.content = ft.Text(
                t("common.processing") if state.is_processing else t("pdf_split.split_btn"),
                weight=ft.FontWeight.BOLD, color=COLORS["text"],
            )
            page.update()

        def _run_split():
            state.is_processing = True
            state.is_cancelled = False
            state.status_text = t("common.initializing")
            state.progress = 0.0
            page.run_thread(_update_ui)

            success_count = 0
            errors = []

            for idx, pdf_path in enumerate(state.files):
                if state.is_cancelled:
                    break

                def on_progress(cur, tot, name):
                    file_pct = idx / len(state.files)
                    inner_pct = cur / tot if tot else 0
                    state.progress = file_pct + inner_pct / len(state.files)
                    state.status_text = t("common.processing")
                    state.detail_text = f"{pdf_path.name} – {name}"
                    page.run_thread(_update_ui)

                try:
                    from utils.files import get_safe_path
                    out_dir = get_safe_path(pdf_path.parent / pdf_path.stem)
                    out_dir.mkdir(exist_ok=True)

                    if state.mode == "pdf":
                        split_to_pages(pdf_path, out_dir, on_progress=on_progress)
                    else:
                        fmt = "PNG" if state.mode == "png" else "JPEG"
                        split_to_images(pdf_path, out_dir, fmt=fmt, dpi=state.dpi, on_progress=on_progress)
                    success_count += 1
                except Exception as exc:
                    errors.append(f"{pdf_path.name}: {exc}")

            state.is_processing = False
            if errors:
                state.status_text = t("common.completed_with_errors")
                state.detail_text = f"{success_count} {t('common.success')}, {len(errors)} {t('common.error')}"
            else:
                state.status_text = t("common.success_msg")
                state.detail_text = t("pdf_split.success_fmt", count=success_count)
            state.progress = 1.0
            page.run_thread(_update_ui)

        def on_split_click(e):
            if state.is_processing or not state.files:
                return
            threading.Thread(target=_run_split, daemon=True).start()

        def on_cancel_click(e):
            if state.is_processing:
                state.is_cancelled = True
            else:
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
        btn_split = ft.ElevatedButton(
            content=ft.Text(
                t("pdf_split.split_btn"),
                weight=ft.FontWeight.BOLD, color=COLORS["text"],
            ),
            bgcolor=COLORS["accent"],
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=RADII["sm"]),
            ),
            height=36, on_click=on_split_click, expand=True,
            disabled=not state.files,
        )

        if not state.files:
            status_text.value = t("pdf_split.no_files")
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
                            controls=[btn_cancel, btn_split],
                            spacing=SPACING["sm"],
                        ),
                    ],
                ),
            )
        )

    ft.app(target=main)
