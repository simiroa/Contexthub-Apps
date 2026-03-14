"""YouTube / Video Downloader – Flet UI."""

from __future__ import annotations

import base64
import os
import threading
import time
from pathlib import Path
from typing import List, Optional

import flet as ft

from contexthub.ui.flet.tokens import COLORS, SPACING, RADII, WINDOWS
from contexthub.ui.flet.theme import configure_page
from utils.i18n import t

from features.video.state import VideoDownloaderState, DownloadItem
from features.video import service


# ── window helper ──

def _apply_compact_window(page: ft.Page, title: str):
    configure_page(page, title)
    preset = WINDOWS["compact"]
    page.window_width = preset["width"]
    page.window_height = 680  # slightly taller for download list
    page.window_min_width = preset["min_width"]
    page.window_min_height = 560


# ── quality label mapping (locale-aware) ──

def _quality_options() -> list[tuple[str, str]]:
    """Returns list of (display_label, quality_key) tuples."""
    return [
        (t("youtube_downloader.format_best"), "Best Video+Audio"),
        (t("youtube_downloader.format_4k"), "4K (2160p)"),
        (t("youtube_downloader.format_1080p"), "1080p"),
        (t("youtube_downloader.format_720p"), "720p"),
        (t("youtube_downloader.format_mp3"), "Audio Only (MP3)"),
        (t("youtube_downloader.format_m4a"), "Audio Only (M4A)"),
    ]


# ── entry point ──

def start_app(targets: List[str] | None = None):
    """Entry point called from main.py."""

    service.migrate_download_history()

    def main(page: ft.Page):
        capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        state = VideoDownloaderState()
        settings = service.load_settings()
        state.download_path = settings.get("download_path", str(Path.home() / "Downloads"))

        _apply_compact_window(page, t("youtube_downloader.title"))

        quality_opts = _quality_options()
        quality_label_to_key = {label: key for label, key in quality_opts}

        # ── controls ──
        url_field = ft.TextField(
            hint_text=t("youtube_downloader.url_placeholder"),
            border_color=COLORS["line"],
            bgcolor=COLORS["field_bg"],
            color=COLORS["text"],
            height=42,
            border_radius=RADII["sm"],
            expand=True,
            text_size=13,
            on_submit=lambda e: _on_analyze(e),
        )

        btn_analyze = ft.ElevatedButton(
            content=ft.Text(
                t("youtube_downloader.search_btn"),
                weight=ft.FontWeight.BOLD,
                color=COLORS["text"],
            ),
            bgcolor=COLORS["accent"],
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
            height=42,
            width=90,
            on_click=lambda e: _on_analyze(e),
        )

        # preview
        thumb_image = ft.Image(
            src="",
            width=120,
            height=68,
            fit=ft.BoxFit.COVER,
            border_radius=RADII["sm"],
            visible=False,
        )
        thumb_placeholder = ft.Container(
            content=ft.Text(
                t("youtube_downloader.no_media"),
                size=10,
                color=COLORS["text_soft"],
                text_align=ft.TextAlign.CENTER,
            ),
            width=120,
            height=68,
            bgcolor=COLORS["surface"],
            border_radius=RADII["sm"],
            alignment=ft.alignment.Alignment(0, 0),
        )
        lbl_title = ft.Text(
            t("youtube_downloader.title_placeholder"),
            size=13,
            weight=ft.FontWeight.BOLD,
            color=COLORS["text"],
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
        lbl_meta = ft.Text(
            t("youtube_downloader.meta_placeholder"),
            size=11,
            color=COLORS["text_muted"],
        )

        preview_card = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Stack(controls=[thumb_placeholder, thumb_image]),
                    ft.Column(
                        controls=[lbl_title, lbl_meta],
                        spacing=4,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=SPACING["sm"],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
            padding=SPACING["sm"],
        )

        # quality
        quality_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(key=key, text=label) for label, key in quality_opts],
            value="Best Video+Audio",
            border_color=COLORS["line"],
            bgcolor=COLORS["field_bg"],
            color=COLORS["text"],
            height=38,
            text_size=12,
            border_radius=8,
            expand=True,
        )
        subs_check = ft.Checkbox(
            label=t("youtube_downloader.subs"),
            value=False,
            active_color=COLORS["accent"],
            label_style=ft.TextStyle(size=11, color=COLORS["text_muted"]),
        )

        # path
        path_field = ft.TextField(
            value=state.download_path,
            border_color=COLORS["line"],
            bgcolor=COLORS["field_bg"],
            color=COLORS["text"],
            height=36,
            text_size=12,
            border_radius=8,
            expand=True,
        )

        folder_picker = None
        if not capture_mode:
            folder_picker = ft.FilePicker()
            page.overlay.append(folder_picker)

        def _on_folder_result(e: ft.FilePickerResultEvent):
            if e.path:
                path_field.value = e.path
                state.download_path = e.path
                settings["download_path"] = e.path
                service.save_settings(settings)
                page.update()

        if folder_picker is not None:
            folder_picker.on_result = _on_folder_result

        def _on_browse(e):
            if folder_picker is not None:
                folder_picker.get_directory_path(
                    dialog_title=t("youtube_downloader.save_path"),
                    initial_directory=state.download_path,
                )

        def _on_open_folder(e):
            import os
            p = path_field.value
            if p and Path(p).exists():
                os.startfile(p)

        btn_browse = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            icon_color=COLORS["text_muted"],
            icon_size=18,
            tooltip=t("youtube_downloader.save_path"),
            on_click=_on_browse,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )
        btn_open = ft.IconButton(
            icon=ft.Icons.OPEN_IN_NEW,
            icon_color=COLORS["text_muted"],
            icon_size=18,
            tooltip=t("utilities_common.open_folder"),
            on_click=_on_open_folder,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

        # action buttons
        btn_queue = ft.ElevatedButton(
            content=ft.Text(
                t("youtube_downloader.add_to_queue"),
                weight=ft.FontWeight.BOLD,
                color=COLORS["text"],
                size=12,
            ),
            bgcolor=COLORS["surface"],
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, COLORS["line"]),
                shape=ft.RoundedRectangleBorder(radius=RADII["sm"]),
            ),
            height=42,
            expand=True,
            disabled=True,
            on_click=lambda e: _on_add_queue(e),
        )
        btn_download = ft.ElevatedButton(
            content=ft.Text(
                t("youtube_downloader.download_now"),
                weight=ft.FontWeight.BOLD,
                color=COLORS["text"],
                size=13,
            ),
            bgcolor=COLORS["accent"],
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
            height=42,
            expand=True,
            disabled=True,
            on_click=lambda e: _on_download(e),
        )

        # downloads list
        downloads_column = ft.Column(
            controls=[],
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
        )

        btn_update = ft.TextButton(
            content=ft.Text(
                "Update Engine (Fix 403)",
                size=10,
                color=COLORS["text_soft"],
            ),
            on_click=lambda e: _on_update_engine(e),
        )

        # ── widget refs for download rows ──
        dl_widgets: dict = {}  # dl_id -> {row, status_lbl, progress}

        # ── handlers ──

        def _refresh_page():
            try:
                page.update()
            except Exception:
                pass

        def _on_analyze(e):
            url = url_field.value.strip() if url_field.value else ""
            if not url:
                return
            state.is_analyzing = True
            btn_analyze.disabled = True
            btn_analyze.content = ft.Text("...", color=COLORS["text"])
            _refresh_page()

            def _worker():
                try:
                    info = service.analyze_url(url)
                    state.video_info = info

                    # update preview
                    lbl_title.value = info.get("title", "Unknown")
                    uploader = info.get("uploader", "Unknown")
                    duration = info.get("duration_string", "??:??")
                    lbl_meta.value = f"{uploader} | {duration}"

                    # thumbnail
                    thumb_url = info.get("thumbnail")
                    if thumb_url:
                        raw = service.fetch_thumbnail_bytes(thumb_url)
                        if raw:
                            b64 = base64.b64encode(raw).decode()
                            thumb_image.src_base64 = b64
                            thumb_image.visible = True

                    btn_download.disabled = False
                    btn_queue.disabled = False
                except Exception as exc:
                    err = str(exc)
                    lbl_title.value = f"Error: {err[:80]}"
                    lbl_meta.value = ""
                    state.video_info = None
                finally:
                    state.is_analyzing = False
                    btn_analyze.disabled = False
                    btn_analyze.content = ft.Text(
                        t("youtube_downloader.search_btn"),
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text"],
                    )
                    page.run_thread(_refresh_page)

            threading.Thread(target=_worker, daemon=True).start()

        def _create_dl_row(dl_id: int, title: str, status_text: str = ""):
            status_lbl = ft.Text(
                status_text or t("youtube_downloader.status_queued"),
                size=10,
                color=COLORS["accent"],
                width=80,
                text_align=ft.TextAlign.RIGHT,
            )
            progress = ft.ProgressBar(
                value=0,
                height=4,
                color=COLORS["accent"],
                bgcolor=COLORS["line"],
                border_radius=2,
                expand=True,
            )
            row = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    title,
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLORS["text"],
                                    expand=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                status_lbl,
                            ],
                        ),
                        progress,
                    ],
                    spacing=4,
                ),
                bgcolor=COLORS["surface"],
                border_radius=RADII["sm"],
                border=ft.border.all(1, COLORS["line"]),
                padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=6),
            )
            dl_widgets[dl_id] = {
                "row": row,
                "status_lbl": status_lbl,
                "progress": progress,
            }
            downloads_column.controls.append(row)
            _refresh_page()

        def _update_dl_status(dl_id: int, text: str, progress_val: float, color: str | None = None):
            w = dl_widgets.get(dl_id)
            if not w:
                return
            w["status_lbl"].value = text
            w["progress"].value = progress_val
            if color:
                w["status_lbl"].color = color
            page.run_thread(_refresh_page)

        def _get_current_opts() -> dict:
            return {
                "quality": quality_dropdown.value or "Best Video+Audio",
                "subs": subs_check.value or False,
                "path": path_field.value or state.download_path,
            }

        def _do_download(dl_id: int, info: dict, opts: dict):
            """Run a single download (called in worker thread)."""
            _update_dl_status(dl_id, t("youtube_downloader.status_starting"), 0.0)

            url = info.get("webpage_url") or info.get("original_url", "")

            def _hook(d, _id=dl_id):
                if d.get("status") == "downloading":
                    try:
                        ps = d.get("_percent_str", "0%").replace("%", "")
                        val = float(ps) / 100
                        _update_dl_status(_id, f"{d.get('_percent_str')}", val)
                    except Exception:
                        pass

            ydl_opts = service.build_ydl_opts(
                quality_key=opts["quality"],
                subs=opts["subs"],
                download_path=opts["path"],
                progress_hook=_hook,
            )

            try:
                service.download_video(url, ydl_opts)
                service.record_download_history(info, opts)
                _update_dl_status(dl_id, t("youtube_downloader.status_complete"), 1.0, COLORS["success"])
            except Exception:
                _update_dl_status(dl_id, t("youtube_downloader.status_failed"), 0.0, COLORS["danger"])

        def _on_download(e):
            if not state.video_info:
                return
            dl_id = state.download_counter
            state.download_counter += 1
            info = state.video_info.copy()
            opts = _get_current_opts()
            _create_dl_row(dl_id, info.get("title", "Unknown"))
            threading.Thread(target=_do_download, args=(dl_id, info, opts), daemon=True).start()

        def _on_add_queue(e):
            if not state.video_info:
                return
            dl_id = state.download_counter
            state.download_counter += 1
            info = state.video_info.copy()
            opts = _get_current_opts()
            _create_dl_row(dl_id, info.get("title", "Unknown"), t("youtube_downloader.status_queued"))

            dl_item = DownloadItem(id=dl_id, title=info.get("title", ""))
            state.downloads.append(dl_item)

            if not state.is_queue_running:
                def _queue_worker():
                    state.is_queue_running = True
                    while state.downloads:
                        item = state.downloads.pop(0)
                        _do_download(item.id, info, opts)
                        time.sleep(1)
                    state.is_queue_running = False

                threading.Thread(target=_queue_worker, daemon=True).start()

        def _on_update_engine(e):
            btn_update.disabled = True
            btn_update.content = ft.Text("Updating...", size=10, color=COLORS["text_soft"])
            _refresh_page()

            def _worker():
                try:
                    service.update_engine()
                    btn_update.content = ft.Text("Updated ✓", size=10, color=COLORS["success"])
                except Exception as exc:
                    btn_update.content = ft.Text(f"Failed: {exc}", size=10, color=COLORS["danger"])
                finally:
                    btn_update.disabled = False
                    page.run_thread(_refresh_page)

            threading.Thread(target=_worker, daemon=True).start()

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
                        # header label
                        ft.Text(
                            "📺 " + t("youtube_downloader.title"),
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS["text"],
                        ),
                        # URL + source settings
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        t("youtube_downloader.source_settings"),
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color=COLORS["text"],
                                    ),
                                    ft.Row(
                                        controls=[url_field, btn_analyze],
                                        spacing=SPACING["xs"],
                                    ),
                                    preview_card,
                                    ft.Row(
                                        controls=[quality_dropdown, subs_check],
                                        spacing=SPACING["sm"],
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=SPACING["xs"],
                            ),
                            bgcolor=COLORS["surface"],
                            border_radius=RADII["md"],
                            border=ft.border.all(1, COLORS["line"]),
                            padding=SPACING["sm"],
                        ),
                        # save path
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        t("youtube_downloader.save_path"),
                                        size=10,
                                        weight=ft.FontWeight.BOLD,
                                        color=COLORS["text_muted"],
                                    ),
                                    ft.Row(
                                        controls=[path_field, btn_browse, btn_open],
                                        spacing=4,
                                    ),
                                ],
                                spacing=4,
                            ),
                            bgcolor=COLORS["surface"],
                            border_radius=RADII["md"],
                            border=ft.border.all(1, COLORS["line"]),
                            padding=SPACING["sm"],
                        ),
                        # action buttons
                        ft.Row(
                            controls=[btn_queue, btn_download],
                            spacing=SPACING["sm"],
                        ),
                        # update engine
                        ft.Row(
                            controls=[ft.Container(expand=True), btn_update],
                        ),
                        # progress section
                        ft.Text(
                            t("youtube_downloader.progress"),
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS["text_muted"],
                        ),
                        ft.Container(
                            content=downloads_column,
                            bgcolor=COLORS["surface"],
                            border_radius=RADII["md"],
                            border=ft.border.all(1, COLORS["line"]),
                            padding=SPACING["xs"],
                            expand=True,
                        ),
                    ],
                ),
            )
        )

    ft.app(target=main)
