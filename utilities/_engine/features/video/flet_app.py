"""YouTube / Video Downloader – Flet UI."""

from __future__ import annotations

import base64
import os
import threading
import time
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.layout import (
    action_bar,
    apply_button_sizing,
    compact_meta_strip,
    icon_action_button,
    integrated_title_bar,
    section_card,
    status_badge,
)
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.window import reveal_desktop_window
from utils.i18n import t

from features.video import service
from features.video.state import DownloadItem, VideoDownloaderState


def _quality_options() -> list[tuple[str, str]]:
    return [
        (t("youtube_downloader.format_best"), "Best Video+Audio"),
        (t("youtube_downloader.format_4k"), "4K (2160p)"),
        (t("youtube_downloader.format_1080p"), "1080p"),
        (t("youtube_downloader.format_720p"), "720p"),
        (t("youtube_downloader.format_mp3"), "Audio Only (MP3)"),
        (t("youtube_downloader.format_m4a"), "Audio Only (M4A)"),
    ]


def _quality_label(value: str, options: list[tuple[str, str]]) -> str:
    for label, key in options:
        if key == value:
            return label
    return value


def start_app(targets: List[str] | None = None):
    service.migrate_download_history()

    async def main(page: ft.Page):
        capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"

        state = VideoDownloaderState()
        settings = service.load_settings()
        state.download_path = settings.get("download_path") or str(Path.home() / "Downloads")

        configure_page(page, t("youtube_downloader.title"), window_profile="form")
        page.bgcolor = COLORS["app_bg"]

        quality_opts = _quality_options()
        state.quality = quality_opts[0][1]

        # header/status
        queue_badge = status_badge("0 queued", "muted")
        quality_badge = status_badge(_quality_label(state.quality, quality_opts), "accent")
        path_badge = status_badge(Path(state.download_path).name or "Downloads", "muted")
        status_text = ft.Text(t("common.ready", "Ready"), size=12, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        # input controls
        url_field = ft.TextField(
            label="URL",
            hint_text=t("youtube_downloader.url_placeholder"),
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            color=COLORS["text"],
            expand=True,
            on_submit=lambda e: on_analyze(),
        )
        analyze_btn = apply_button_sizing(
            ft.ElevatedButton(
                t("youtube_downloader.search_btn"),
                on_click=lambda e: on_analyze(),
                bgcolor=COLORS["accent"],
                color=COLORS["text"],
            ),
            "compact",
        )

        quality_dropdown = ft.Dropdown(
            label=t("youtube_downloader.format_label", "Format"),
            value=state.quality,
            options=[ft.dropdown.Option(key=key, text=label) for label, key in quality_opts],
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            dense=True,
            expand=True,
        )
        subs_check = ft.Checkbox(label=t("youtube_downloader.subs"), value=False, scale=0.95)
        quality_dropdown.on_change = lambda e: sync_meta()
        subs_check.on_change = lambda e: sync_meta()

        path_field = ft.TextField(
            label=t("youtube_downloader.save_path"),
            value=state.download_path,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            color=COLORS["text"],
            expand=True,
            on_change=lambda e: on_path_change(e.control.value),
        )

        folder_picker = None
        if not capture_mode:
            folder_picker = ft.FilePicker()
            page.overlay.append(folder_picker)

        def on_folder_result(e: ft.FilePickerResultEvent):
            if e.path:
                path_field.value = e.path
                on_path_change(e.path)
                page.update()

        if folder_picker is not None:
            folder_picker.on_result = on_folder_result

        browse_btn = icon_action_button(
            ft.Icons.FOLDER_OPEN,
            tooltip=t("youtube_downloader.save_path"),
            on_click=lambda e: folder_picker.get_directory_path(dialog_title=t("youtube_downloader.save_path"), initial_directory=state.download_path) if folder_picker else None,
        )
        open_btn = icon_action_button(
            ft.Icons.OPEN_IN_NEW,
            tooltip=t("common.open", "Open"),
            on_click=lambda e: os.startfile(path_field.value) if path_field.value and Path(path_field.value).exists() else None,
        )

        # preview
        thumb_placeholder = ft.Container(
            width=160,
            height=90,
            border_radius=RADII["sm"],
            bgcolor=COLORS["surface_alt"],
            alignment=ft.alignment.Alignment(0, 0),
            content=ft.Text(t("youtube_downloader.no_media"), size=11, color=COLORS["text_soft"], text_align=ft.TextAlign.CENTER),
        )
        thumb_image = ft.Image(src="", width=160, height=90, fit=ft.BoxFit.COVER, border_radius=RADII["sm"])
        thumb_host = ft.Container(width=160, height=90, border_radius=RADII["sm"], clip_behavior=ft.ClipBehavior.ANTI_ALIAS, content=thumb_placeholder)
        title_text = ft.Text(t("youtube_downloader.title_placeholder"), size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
        meta_text = ft.Text(t("youtube_downloader.meta_placeholder"), size=11, color=COLORS["text_muted"])

        preview_card = ft.Container(
            bgcolor=COLORS["surface_alt"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            padding=SPACING["md"],
            content=ft.Row(
                [
                    thumb_host,
                    ft.Column(
                        [
                            title_text,
                            meta_text,
                            ft.Text("Analyze a link to preview title, channel, duration, and thumbnail.", size=11, color=COLORS["text_soft"]),
                        ],
                        spacing=SPACING["xs"],
                        expand=True,
                    ),
                ],
                spacing=SPACING["sm"],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # queue
        queue_column = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        queue_widgets: dict[int, dict[str, ft.Control]] = {}

        def add_queue_hint():
            if queue_column.controls:
                return
            queue_column.controls.append(
                ft.Container(
                    padding=SPACING["md"],
                    bgcolor=COLORS["surface_alt"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    content=ft.Text("Add a URL and queue a download to see progress here.", color=COLORS["text_muted"]),
                )
            )

        def remove_queue_hint():
            queue_column.controls = [c for c in queue_column.controls if getattr(c, "data", None) != "queue_hint"]

        def make_queue_row(item: DownloadItem, status_value: str):
            status_label = ft.Text(status_value, size=10, color=COLORS["accent"], width=90, text_align=ft.TextAlign.RIGHT)
            progress = ft.ProgressBar(value=item.progress, color=COLORS["accent"], bgcolor=COLORS["line"], height=4)
            row = ft.Container(
                bgcolor=COLORS["surface_alt"],
                border=ft.border.all(1, COLORS["line"]),
                border_radius=RADII["sm"],
                padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(item.title or t("youtube_downloader.title_placeholder"), expand=True, size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                status_label,
                            ]
                        ),
                        ft.Text(f"{item.quality} | {'subs' if item.subs else 'no subs'}", size=10, color=COLORS["text_soft"]),
                        progress,
                    ],
                    spacing=4,
                ),
            )
            queue_widgets[item.id] = {"status": status_label, "progress": progress}
            queue_column.controls.append(row)

        def update_queue_row(item_id: int, text: str, progress_value: float, color: str | None = None):
            widgets = queue_widgets.get(item_id)
            if not widgets:
                return
            widgets["status"].value = text
            widgets["progress"].value = progress_value
            if color:
                widgets["status"].color = color
            page.run_thread(page.update)

        # actions
        queue_btn = icon_action_button(
            ft.Icons.ADD,
            tooltip=t("youtube_downloader.add_to_queue"),
            disabled=True,
        )
        download_btn = apply_button_sizing(ft.ElevatedButton(t("youtube_downloader.download_now"), disabled=True, bgcolor=COLORS["accent"], color=COLORS["text"]), "primary")
        update_btn = icon_action_button(
            ft.Icons.SYSTEM_UPDATE_ALT,
            tooltip="Update engine",
        )

        def sync_meta():
            count = len(queue_widgets)
            queue_badge.content.value = f"{count} queued"
            quality_badge.content.value = _quality_label(quality_dropdown.value or state.quality, quality_opts)
            path_badge.content.value = Path(path_field.value or state.download_path).name or "Downloads"
            page.update()

        def set_preview_empty():
            thumb_host.content = thumb_placeholder

        def on_path_change(value: str):
            state.download_path = value.strip() or str(Path.home() / "Downloads")
            settings["download_path"] = state.download_path
            service.save_settings(settings)
            sync_meta()

        def current_opts() -> dict:
            return {
                "quality": quality_dropdown.value or state.quality,
                "subs": bool(subs_check.value),
                "path": path_field.value.strip() or state.download_path,
            }

        def build_item() -> DownloadItem | None:
            if not state.video_info:
                return None
            info = state.video_info
            opts = current_opts()
            item = DownloadItem(
                id=state.download_counter,
                title=info.get("title") or t("youtube_downloader.title_placeholder"),
                webpage_url=info.get("webpage_url") or info.get("original_url") or "",
                quality=opts["quality"],
                subs=opts["subs"],
                path=opts["path"],
            )
            state.download_counter += 1
            return item

        def update_overall_progress(value: float, visible: bool):
            progress_bar.visible = visible
            progress_bar.value = value
            page.run_thread(page.update)

        def do_download(item: DownloadItem):
            def hook(data):
                if data.get("status") != "downloading":
                    return
                try:
                    percent = float(str(data.get("_percent_str", "0")).replace("%", ""))
                except Exception:
                    percent = 0.0
                update_queue_row(item.id, data.get("_percent_str", "0%"), percent / 100.0)
                update_overall_progress(percent / 100.0, True)

            update_queue_row(item.id, t("youtube_downloader.status_starting"), 0.0)
            opts = service.build_ydl_opts(item.quality, item.subs, item.path, progress_hook=hook)
            try:
                service.download_video(item.webpage_url, opts)
                service.record_download_history(
                    {"title": item.title, "webpage_url": item.webpage_url, "original_url": item.webpage_url},
                    {"quality": item.quality, "subs": item.subs, "path": item.path},
                )
                update_queue_row(item.id, t("youtube_downloader.status_complete"), 1.0, COLORS["success"])
            except Exception as exc:
                update_queue_row(item.id, f"{t('youtube_downloader.status_failed')}: {str(exc)[:80]}", 0.0, COLORS["danger"])
            finally:
                update_overall_progress(0.0, False)

        def on_download_now():
            item = build_item()
            if item is None or not item.webpage_url:
                status_text.value = "No analyzed URL to download."
                page.update()
                return
            if queue_column.controls and getattr(queue_column.controls[0], "data", None) == "queue_hint":
                queue_column.controls.clear()
            make_queue_row(item, t("youtube_downloader.status_starting"))
            sync_meta()
            threading.Thread(target=lambda: do_download(item), daemon=True).start()

        def on_queue():
            item = build_item()
            if item is None or not item.webpage_url:
                return
            if queue_column.controls and getattr(queue_column.controls[0], "data", None) == "queue_hint":
                queue_column.controls.clear()
            make_queue_row(item, t("youtube_downloader.status_queued"))
            state.downloads.append(item)
            sync_meta()

            if state.is_queue_running:
                return

            def queue_worker():
                state.is_queue_running = True
                while state.downloads:
                    queued = state.downloads.pop(0)
                    do_download(queued)
                    time.sleep(0.5)
                state.is_queue_running = False

            threading.Thread(target=queue_worker, daemon=True).start()

        def on_update_engine():
            update_btn.disabled = True
            update_btn.tooltip = "Updating engine..."
            status_text.value = "Updating engine..."
            page.update()

            def worker():
                try:
                    service.update_engine()
                    update_btn.tooltip = "Engine updated"
                    status_text.value = "Engine updated"
                except Exception as exc:
                    update_btn.tooltip = "Engine update failed"
                    status_text.value = f"Update failed: {str(exc)[:80]}"
                finally:
                    update_btn.disabled = False
                    page.run_thread(page.update)

            threading.Thread(target=worker, daemon=True).start()

        def on_analyze():
            url = (url_field.value or "").strip()
            if not url:
                return

            state.is_analyzing = True
            analyze_btn.disabled = True
            analyze_btn.text = "..."
            status_text.value = "Analyzing..."
            detail_text.value = ""
            page.update()

            def worker():
                try:
                    info = service.analyze_url(url)
                    state.video_info = info
                    state.url = url
                    title_text.value = info.get("title") or t("youtube_downloader.title_placeholder")
                    meta_text.value = f"{info.get('uploader', 'Unknown')} | {info.get('duration_string', '??:??')}"
                    thumb_url = info.get("thumbnail")
                    if thumb_url:
                        raw = service.fetch_thumbnail_bytes(thumb_url)
                        if raw:
                            thumb_image.src_base64 = base64.b64encode(raw).decode()
                            thumb_host.content = thumb_image
                        else:
                            set_preview_empty()
                    else:
                        set_preview_empty()
                    queue_btn.disabled = False
                    download_btn.disabled = False
                    status_text.value = t("common.ready", "Ready")
                except Exception as exc:
                    state.video_info = None
                    title_text.value = t("youtube_downloader.title_placeholder")
                    meta_text.value = str(exc)[:120]
                    set_preview_empty()
                    queue_btn.disabled = True
                    download_btn.disabled = True
                    status_text.value = "Analyze failed"
                    detail_text.value = str(exc)[:200]
                finally:
                    state.is_analyzing = False
                    analyze_btn.disabled = False
                    analyze_btn.text = t("youtube_downloader.search_btn")
                    page.run_thread(page.update)

            threading.Thread(target=worker, daemon=True).start()

        queue_btn.on_click = lambda e: on_queue()
        download_btn.on_click = lambda e: on_download_now()
        update_btn.on_click = lambda e: on_update_engine()

        source_card = section_card(
            "Source",
            ft.Column(
                [
                    ft.Row([url_field, analyze_btn], spacing=SPACING["sm"]),
                    preview_card,
                    ft.Row([quality_dropdown, subs_check], spacing=SPACING["sm"], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    action_bar(
                        status=ft.Column([status_text, detail_text], spacing=2, tight=True),
                        progress=progress_bar,
                        primary=download_btn,
                        secondary=[queue_btn, update_btn],
                        embedded=True,
                    ),
                ],
                spacing=SPACING["sm"],
            ),
        )
        output_card = section_card(
            "Output",
            ft.Column(
                [
                    path_field,
                    ft.Row([browse_btn, open_btn], spacing=SPACING["sm"]),
                ],
                spacing=SPACING["sm"],
            ),
        )
        queue_card = section_card("Downloads", ft.Container(content=queue_column, height=260))

        add_queue_hint()
        sync_meta()

        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["sm"],
                    controls=[
                        integrated_title_bar(page, t("youtube_downloader.title")),
                        ft.Container(
                            expand=True,
                            padding=ft.padding.all(SPACING["md"]),
                            content=ft.Column(
                                expand=True,
                                spacing=SPACING["sm"],
                                controls=[
                                    compact_meta_strip(
                                        t("youtube_downloader.title"),
                                        description="Analyze URLs first, then set quality/subtitle options and output path.",
                                        badges=[queue_badge, quality_badge, path_badge],
                                    ),
                                    ft.Row(
                                        expand=True,
                                        spacing=SPACING["sm"],
                                        controls=[
                                            ft.Container(
                                                expand=True,
                                                content=ft.Column([source_card, output_card], spacing=SPACING["sm"]),
                                            ),
                                            ft.Container(width=404, content=queue_card),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            )
        )

        await reveal_desktop_window(page)

    ft.run(main, view=ft.AppView.FLET_APP_HIDDEN)
