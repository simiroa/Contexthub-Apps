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
from utils.ai_runner import kill_process_tree


class DemucsService:
    def __init__(self):
        self.current_process = None
        self.cancel_flag = False

    def run(self, input_paths: List[Path], model: str, output_format: str, mode: str, on_progress, on_complete, on_log):
        self.cancel_flag = False
        total = len(input_paths)
        success = 0
        errors: list[str] = []
        last_output_dir = None
        for index, path in enumerate(input_paths):
            if self.cancel_flag:
                break
            on_progress(index, total, path.name)
            try:
                output_dir = path.parent / "Separated_Audio"
                output_dir.mkdir(parents=True, exist_ok=True)
                cmd = [sys.executable, "-m", "demucs", "-n", model, "-o", str(output_dir), str(path)]
                if output_format == "mp3":
                    cmd.append("--mp3")
                elif output_format == "flac":
                    cmd.append("--flac")
                if "2" in mode:
                    cmd.append("--two-stems=vocals")
                on_log("Running command: " + " ".join(cmd))
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                for line in self.current_process.stdout:
                    if self.cancel_flag:
                        break
                    on_log(line.strip())
                self.current_process.wait()
                if self.cancel_flag:
                    break
                if self.current_process.returncode != 0:
                    raise RuntimeError(f"Demucs exited with code {self.current_process.returncode}")
                success += 1
                last_output_dir = output_dir
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        on_complete(success, total, errors, last_output_dir)

    def cancel(self):
        self.cancel_flag = True
        if self.current_process:
            kill_process_tree(self.current_process)
            self.current_process = None


def start_app(targets: List[str] | None = None):
    async def main(page: ft.Page):
        configure_page(page, "Demucs Stem Separation", window_profile="form")
        page.bgcolor = COLORS["app_bg"]
        title = "Demucs Stem Separation"

        audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"}
        input_paths = [Path(path) for path in (targets or []) if Path(path).suffix.lower() in audio_exts]
        service = DemucsService()
        state = {"processing": False, "progress": 0.0, "status": "Ready", "last_output_dir": None}
        prefs = load_ui_prefs(
            "demucs_stems",
            {"model": "htdemucs", "format": "mp3", "mode": "All Stems (4)"},
        )

        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        for src in input_paths:
            file_list.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
                    bgcolor=COLORS["surface_alt"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    content=ft.Row([ft.Icon(ft.Icons.AUDIO_FILE, size=16, color=COLORS["text_muted"]), ft.Text(src.name, size=12)], spacing=SPACING["sm"]),
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
                            ft.Text("No audio files yet.", color=COLORS["text"]),
                            ft.Text("Launch from the context menu on one or more source files.", color=COLORS["text_muted"]),
                        ],
                    ),
                )
            )

        def persist_prefs(_=None):
            save_ui_prefs(
                "demucs_stems",
                {"model": model_dropdown.value, "format": format_dropdown.value, "mode": mode_dropdown.value},
            )

        model_dropdown = ft.Dropdown(label="Demucs Model", options=[ft.dropdown.Option("htdemucs"), ft.dropdown.Option("htdemucs_ft"), ft.dropdown.Option("mdx_extra_q"), ft.dropdown.Option("hdemucs_mmi")], value=prefs["model"], bgcolor=COLORS["field_bg"], border_color=COLORS["line"], expand=True, on_select=persist_prefs)
        format_dropdown = ft.Dropdown(label="Output Format", options=[ft.dropdown.Option("wav"), ft.dropdown.Option("mp3"), ft.dropdown.Option("flac")], value=prefs["format"], bgcolor=COLORS["field_bg"], border_color=COLORS["line"], expand=True, on_select=persist_prefs)
        mode_dropdown = ft.Dropdown(label="Separation Mode", options=[ft.dropdown.Option("All Stems (4)"), ft.dropdown.Option("Vocals vs Backing (2)")], value=prefs["mode"], bgcolor=COLORS["field_bg"], border_color=COLORS["line"], expand=True, on_select=persist_prefs)

        log_lines = ft.Column(spacing=4, scroll=ft.ScrollMode.ADAPTIVE, controls=[ft.Text("Logs will appear here after the task starts.", size=11, font_family="Consolas", color=COLORS["text_muted"])])
        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])
        open_btn = ft.OutlinedButton(content=ft.Text("Open Output Folder"), visible=False, on_click=lambda e: os.startfile(str(state["last_output_dir"])) if state["last_output_dir"] and Path(state["last_output_dir"]).exists() else None)

        def update_ui():
            progress_bar.visible = state["processing"] or state["progress"] > 0
            progress_bar.value = state["progress"]
            status_text.value = "Ready. Add audio files to enable separation." if not input_paths and not state["processing"] else state["status"]
            run_btn.disabled = state["processing"] or not input_paths
            cancel_btn.disabled = not state["processing"]
            open_btn.visible = state["last_output_dir"] is not None
            page.update()

        def on_progress(current, total, filename):
            state["progress"] = 0 if total == 0 else current / total
            state["status"] = f"Processing {current + 1}/{total}: {filename}"
            page.run_thread(update_ui)

        def on_log(message: str):
            if len(log_lines.controls) == 1 and isinstance(log_lines.controls[0], ft.Text) and log_lines.controls[0].value.startswith("Logs will"):
                log_lines.controls = []
            log_lines.controls.append(ft.Text(message, size=11, font_family="Consolas", color=COLORS["text_muted"]))
            if len(log_lines.controls) > 120:
                log_lines.controls = log_lines.controls[-120:]
            page.run_thread(page.update)

        def on_complete(success, total, errors, last_output_dir):
            state["processing"] = False
            state["progress"] = 1.0 if total else 0
            state["status"] = f"Complete: {success}/{total} success"
            state["last_output_dir"] = last_output_dir
            page.run_thread(update_ui)
            message = f"Processed {success}/{total} files."
            if errors:
                message += "\n\n" + "\n".join(errors[:5])
            dialog = ft.AlertDialog(title=ft.Text("Demucs Complete"), content=ft.Text(message), actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))])
            page.open(dialog)

        def run_task(e: ft.ControlEvent):
            if not input_paths:
                return
            state["processing"] = True
            state["progress"] = 0
            state["status"] = "Preparing separation..."
            state["last_output_dir"] = None
            log_lines.controls = [ft.Text("Starting Demucs...", size=11, font_family="Consolas", color=COLORS["text_muted"])]
            update_ui()
            threading.Thread(target=service.run, args=(input_paths, model_dropdown.value, format_dropdown.value, mode_dropdown.value, on_progress, on_complete, on_log), daemon=True).start()

        def cancel_task(e: ft.ControlEvent):
            service.cancel()
            state["status"] = "Cancelling..."
            update_ui()

        summary = ft.Container(padding=SPACING["lg"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["lg"], content=ft.Column(spacing=SPACING["sm"], controls=[ft.Text("Demucs Stem Separation", size=24, weight=ft.FontWeight.BOLD), ft.Text("Split songs into stems or vocals/backing tracks with a shared Demucs workflow.", color=COLORS["text_muted"]), ft.Text(f"{len(input_paths)} files queued", color=COLORS["text_muted"])]))
        files_card = ft.Container(padding=SPACING["md"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["md"], content=ft.Column(spacing=SPACING["sm"], controls=[ft.Text("Input Files", size=16, weight=ft.FontWeight.BOLD), ft.Container(content=file_list, height=150)]))
        settings_card = ft.Container(padding=SPACING["md"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["md"], content=ft.Column(spacing=SPACING["md"], controls=[ft.Text("Extraction Settings", size=16, weight=ft.FontWeight.BOLD), model_dropdown, ft.Row([format_dropdown, mode_dropdown], spacing=SPACING["sm"])]))
        logs_card = ft.Container(padding=SPACING["md"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["md"], content=ft.Column(spacing=SPACING["sm"], controls=[ft.Text("Execution Log", size=16, weight=ft.FontWeight.BOLD), ft.Container(content=log_lines, height=170)]))

        run_btn = ft.ElevatedButton(content=ft.Text("Start Separation"), on_click=run_task, bgcolor=COLORS["accent"], color=COLORS["text"])
        cancel_btn = ft.OutlinedButton(content=ft.Text("Cancel"), on_click=cancel_task, disabled=True)
        apply_button_sizing(run_btn, "primary")
        apply_button_sizing(cancel_btn, "compact")
        apply_button_sizing(open_btn, "compact")

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
                                    action_bar(
                                        status=status_text,
                                        progress=progress_bar,
                                        primary=run_btn,
                                        secondary=[cancel_btn, open_btn],
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
