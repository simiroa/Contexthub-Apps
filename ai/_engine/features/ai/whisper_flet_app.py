from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.layout import action_bar, apply_button_sizing, integrated_title_bar
from contexthub.ui.flet.prefs import load_ui_prefs, save_ui_prefs
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.window import reveal_desktop_window


def start_app(targets: List[str] | None = None):
    async def main(page: ft.Page):
        configure_page(page, "Whisper Subtitle AI", window_profile="form")
        page.bgcolor = COLORS["app_bg"]
        title = "Whisper Subtitle AI"

        media_exts = {".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".m4a"}
        input_paths = [Path(path) for path in (targets or []) if Path(path).suffix.lower() in media_exts]
        state = {"processing": False, "progress": 0.0, "status": "Ready", "current_process": None}
        prefs = load_ui_prefs(
            "whisper_subtitle",
            {
                "model": "small",
                "task": "transcribe",
                "device": "cuda",
                "language": "Auto",
                "output_dir": "",
                "fmt_srt": True,
                "fmt_vtt": False,
                "fmt_txt": False,
                "fmt_json": False,
            },
        )

        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        for src in input_paths:
            file_list.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
                    bgcolor=COLORS["surface_alt"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    content=ft.Row([ft.Icon(ft.Icons.SUBTITLES, size=16, color=COLORS["text_muted"]), ft.Text(src.name, size=12)], spacing=SPACING["sm"]),
                )
            )
        if not file_list.controls:
            file_list.controls.append(
                ft.Container(
                    padding=SPACING["md"],
                    bgcolor=COLORS["surface_alt"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    content=ft.Column(
                        spacing=SPACING["xs"],
                        controls=[
                            ft.Text("No media files yet.", color=COLORS["text"]),
                            ft.Text("Launch from the context menu on one or more supported media files.", color=COLORS["text_muted"]),
                        ],
                    ),
                )
            )

        def persist_prefs(_=None):
            save_ui_prefs(
                "whisper_subtitle",
                {
                    "model": model_dropdown.value,
                    "task": task_dropdown.value,
                    "device": device_dropdown.value,
                    "language": lang_dropdown.value,
                    "output_dir": out_dir.value,
                    "fmt_srt": fmt_srt.value,
                    "fmt_vtt": fmt_vtt.value,
                    "fmt_txt": fmt_txt.value,
                    "fmt_json": fmt_json.value,
                },
            )

        model_dropdown = ft.Dropdown(label="Model", options=[ft.dropdown.Option(name) for name in ["tiny", "base", "small", "medium", "large-v2", "large-v3"]], value=prefs["model"], bgcolor=COLORS["field_bg"], border_color=COLORS["line"], expand=True, on_select=persist_prefs)
        task_dropdown = ft.Dropdown(label="Task", options=[ft.dropdown.Option("transcribe"), ft.dropdown.Option("translate")], value=prefs["task"], bgcolor=COLORS["field_bg"], border_color=COLORS["line"], expand=True, on_select=persist_prefs)
        device_dropdown = ft.Dropdown(label="Device", options=[ft.dropdown.Option("cuda"), ft.dropdown.Option("cpu")], value=prefs["device"], bgcolor=COLORS["field_bg"], border_color=COLORS["line"], expand=True, on_select=persist_prefs)
        lang_dropdown = ft.Dropdown(label="Language", options=[ft.dropdown.Option(name) for name in ["Auto", "en", "ko", "ja", "zh", "es", "fr", "de", "ru", "it"]], value=prefs["language"], bgcolor=COLORS["field_bg"], border_color=COLORS["line"], expand=True, on_select=persist_prefs)
        out_dir = ft.TextField(label="Output Folder", value=prefs["output_dir"], bgcolor=COLORS["field_bg"], border_color=COLORS["line"], on_change=persist_prefs)
        fmt_srt = ft.Checkbox(label="SRT", value=prefs["fmt_srt"], on_change=persist_prefs)
        fmt_vtt = ft.Checkbox(label="VTT", value=prefs["fmt_vtt"], on_change=persist_prefs)
        fmt_txt = ft.Checkbox(label="TXT", value=prefs["fmt_txt"], on_change=persist_prefs)
        fmt_json = ft.Checkbox(label="JSON", value=prefs["fmt_json"], on_change=persist_prefs)

        log_lines = ft.Column(spacing=4, scroll=ft.ScrollMode.ADAPTIVE, controls=[ft.Text("Logs will appear here after generation starts.", size=11, font_family="Consolas", color=COLORS["text_muted"])])
        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        def update_ui():
            progress_bar.visible = state["processing"] or state["progress"] > 0
            progress_bar.value = state["progress"]
            status_text.value = "Ready. Add media files to enable generation." if not input_paths and not state["processing"] else state["status"]
            run_btn.disabled = state["processing"] or not input_paths
            cancel_btn.disabled = not state["processing"]
            page.update()

        def append_log(message: str):
            if len(log_lines.controls) == 1 and isinstance(log_lines.controls[0], ft.Text) and log_lines.controls[0].value.startswith("Logs will"):
                log_lines.controls = []
            log_lines.controls.append(ft.Text(message, size=11, font_family="Consolas", color=COLORS["text_muted"]))
            if len(log_lines.controls) > 150:
                log_lines.controls = log_lines.controls[-150:]
            page.run_thread(page.update)

        def run_batch():
            formats = []
            if fmt_srt.value:
                formats.append("srt")
            if fmt_vtt.value:
                formats.append("vtt")
            if fmt_txt.value:
                formats.append("txt")
            if fmt_json.value:
                formats.append("json")
            if not formats:
                formats.append("srt")
            total = len(input_paths)
            script_path = Path(__file__).resolve().parent / "standalone" / "subtitle_gen.py"

            for index, src in enumerate(input_paths):
                if not state["processing"]:
                    break
                state["progress"] = 0 if total == 0 else index / total
                state["status"] = f"Processing {index + 1}/{total}: {src.name}"
                page.run_thread(update_ui)
                cmd = [sys.executable, str(script_path), str(src), "--model", model_dropdown.value, "--task", task_dropdown.value, "--device", device_dropdown.value, "--format", ",".join(formats)]
                if lang_dropdown.value != "Auto":
                    cmd.extend(["--lang", lang_dropdown.value])
                if out_dir.value.strip():
                    cmd.extend(["--output_dir", out_dir.value.strip()])
                append_log("Running command: " + " ".join(cmd))
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                state["current_process"] = process
                while True:
                    if not state["processing"]:
                        try:
                            process.terminate()
                        except Exception:
                            pass
                        break
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        append_log(line.rstrip())
                process.wait()
                state["current_process"] = None

            state["processing"] = False
            state["progress"] = 1.0 if total else 0
            state["status"] = "Subtitle generation complete"
            page.run_thread(update_ui)

        def start_generation(e: ft.ControlEvent):
            if not input_paths:
                return
            state["processing"] = True
            state["progress"] = 0
            state["status"] = "Preparing generation..."
            log_lines.controls = [ft.Text("Starting Whisper batch...", size=11, font_family="Consolas", color=COLORS["text_muted"])]
            update_ui()
            threading.Thread(target=run_batch, daemon=True).start()

        def cancel_generation(e: ft.ControlEvent):
            state["processing"] = False
            state["status"] = "Cancelling..."
            process = state.get("current_process")
            if process:
                try:
                    process.terminate()
                except Exception:
                    pass
            update_ui()

        summary = ft.Container(padding=SPACING["lg"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["lg"], content=ft.Column(spacing=SPACING["sm"], controls=[ft.Text("Whisper Subtitle AI", size=24, weight=ft.FontWeight.BOLD), ft.Text("Generate subtitles or translated transcripts with Faster-Whisper.", color=COLORS["text_muted"]), ft.Text(f"{len(input_paths)} files queued", color=COLORS["text_muted"])]))
        files_card = ft.Container(padding=SPACING["md"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["md"], content=ft.Column(spacing=SPACING["sm"], controls=[ft.Text("Input Files", size=16, weight=ft.FontWeight.BOLD), ft.Container(content=file_list, height=120)]))
        settings_card = ft.Container(padding=SPACING["md"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["md"], content=ft.Column(spacing=SPACING["md"], controls=[ft.Text("AI Processing Settings", size=16, weight=ft.FontWeight.BOLD), ft.Row([model_dropdown, task_dropdown], spacing=SPACING["sm"]), ft.Row([device_dropdown, lang_dropdown], spacing=SPACING["sm"]), out_dir, ft.Row([fmt_srt, fmt_vtt, fmt_txt, fmt_json], spacing=SPACING["sm"], wrap=True)]))
        logs_card = ft.Container(padding=SPACING["md"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["md"], content=ft.Column(spacing=SPACING["sm"], controls=[ft.Text("Execution Log", size=16, weight=ft.FontWeight.BOLD), ft.Container(content=log_lines, height=170)]))
        run_btn = ft.ElevatedButton(content=ft.Text("Generate Subtitles"), on_click=start_generation, bgcolor=COLORS["accent"], color=COLORS["text"])
        cancel_btn = ft.OutlinedButton(content=ft.Text("Cancel"), on_click=cancel_generation, disabled=True)
        apply_button_sizing(run_btn, "primary")
        apply_button_sizing(cancel_btn, "compact")

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
                            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["md"]),
                            content=ft.Column(
                                expand=True,
                                spacing=SPACING["md"],
                                controls=[
                                    summary,
                                    files_card,
                                    settings_card,
                                    logs_card,
                                    action_bar(status=status_text, progress=progress_bar, primary=run_btn, secondary=[cancel_btn]),
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
