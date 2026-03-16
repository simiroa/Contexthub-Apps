from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import flet as ft

from contexthub.ui.flet.layout import (
    action_bar,
    apply_button_sizing,
    compact_meta_strip,
    integrated_title_bar,
    section_card,
    status_badge,
)
from contexthub.ui.flet.prefs import load_ui_prefs, save_ui_prefs
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.window import reveal_desktop_window
from utils import paths
from utils.ai_runner import start_ai_script


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga", ".tif", ".tiff"}


def _collect_images(targets: list[str] | None) -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for target in targets or []:
        path = Path(target)
        candidates: list[Path]
        if path.is_dir():
            candidates = [item for item in path.iterdir() if item.suffix.lower() in IMAGE_EXTS]
        else:
            candidates = [path] if path.suffix.lower() in IMAGE_EXTS else []
        for item in candidates:
            try:
                resolved = str(item.resolve())
            except Exception:
                resolved = str(item)
            if resolved in seen or not item.exists():
                continue
            seen.add(resolved)
            files.append(item)
    return files


def _file_row(src: Path) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=8),
        bgcolor=COLORS["surface_alt"],
        border=ft.border.all(1, COLORS["line"]),
        border_radius=RADII["sm"],
        content=ft.Row(
            [
                ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=COLORS["text_muted"]),
                ft.Text(src.name, size=12, color=COLORS["text"], expand=True, no_wrap=True),
                ft.Text(src.suffix.upper().lstrip("."), size=10, color=COLORS["text_soft"]),
            ],
            spacing=SPACING["sm"],
        ),
    )


def _realesrgan_dir() -> Path:
    model_root = getattr(paths, "REALESRGAN_DIR", None)
    if model_root:
        return Path(model_root)
    engine_root = Path(__file__).resolve().parents[3]
    return engine_root / "resources" / "ai_models" / "realesrgan"


def _model_status_label() -> tuple[str, str]:
    """Returns (label, tone) for status badge."""
    model_root = _realesrgan_dir()
    model = model_root / "RealESRGAN_x4plus.pth"
    gfpgan = model_root / "GFPGANv1.4.pth"
    if model.exists() and gfpgan.exists():
        return "Models ready", "success"
    if model.exists():
        return "ESRGAN ready", "success"
    return "Models missing", "warning"


def _resolve_output_dir(files: list[Path], custom_output_dir: Path | None) -> Path | None:
    if custom_output_dir:
        return custom_output_dir
    if files:
        return files[0].parent
    return None


def _output_summary(files: list[Path], custom_output_dir: Path | None) -> str:
    if not files:
        return "Output path appears after images are queued."
    out_dir = _resolve_output_dir(files, custom_output_dir)
    return f"{out_dir}\\{files[0].stem}_upscaled.png" if out_dir else "Output path unavailable."

def open_upscale_flet(targets: list[str] | None = None):
    async def main(page: ft.Page):
        files = _collect_images(targets)
        capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        is_running = False
        current_process = None
        folder_picker = None
        prefs = load_ui_prefs(
            "esrgan_upscale",
            {"scale": "4", "face_enhance": False, "use_tile": False, "output_dir": ""},
        )
        custom_output_dir: Path | None = Path(prefs["output_dir"]) if prefs["output_dir"] else None

        configure_page(page, "AI Image Upscaler", window_profile="form")
        page.bgcolor = COLORS["app_bg"]
        if not capture_mode:
            folder_picker = ft.FilePicker()
            page.overlay.append(folder_picker)

        # ── controls ──
        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)
        queue_badge = status_badge(f"{len(files)} files", "muted")
        model_label, model_tone = _model_status_label()
        model_badge = status_badge(model_label, model_tone)
        output_badge = status_badge("Source folder", "muted")
        output_hint = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)

        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        log_box = ft.TextField(
            value="",
            multiline=True,
            read_only=True,
            min_lines=4,
            max_lines=6,
            border_radius=RADII["md"],
            bgcolor=COLORS["surface_alt"],
            border_color=COLORS["line"],
        )

        def persist_prefs():
            save_ui_prefs(
                "esrgan_upscale",
                {
                    "scale": scale_group.value,
                    "face_enhance": face_checkbox.value,
                    "use_tile": tile_checkbox.value,
                    "output_dir": str(custom_output_dir) if custom_output_dir else "",
                },
            )

        scale_group = ft.RadioGroup(
            value=prefs["scale"],
            content=ft.Row(
                controls=[ft.Radio(value="2", label="2x"), ft.Radio(value="4", label="4x")],
                spacing=SPACING["md"],
            ),
            on_change=lambda e: persist_prefs(),
        )
        face_checkbox = ft.Checkbox(label="Face Enhance (GFPGAN)", value=prefs["face_enhance"], scale=0.95, on_change=lambda e: persist_prefs())
        tile_checkbox = ft.Checkbox(label="Use Tiling for low VRAM", value=prefs["use_tile"], scale=0.95, on_change=lambda e: persist_prefs())

        # ── refresh & sync ──
        def refresh_files():
            nonlocal files
            file_list.controls.clear()
            if files:
                for item in files:
                    file_list.controls.append(_file_row(item))
            else:
                file_list.controls.append(
                    ft.Container(
                        padding=SPACING["md"],
                        bgcolor=COLORS["surface_alt"],
                        border=ft.border.all(1, COLORS["line"]),
                        border_radius=RADII["sm"],
                        content=ft.Column(
                            spacing=SPACING["xs"],
                            controls=[
                                ft.Text("No images loaded yet.", color=COLORS["text"]),
                                ft.Text(
                                    "Launch from the context menu on one or more image files.",
                                    color=COLORS["text_muted"],
                                ),
                            ],
                        ),
                    )
                )

        def sync_meta():
            queue_badge.content.value = f"{len(files)} files"
            if custom_output_dir:
                output_badge.content.value = "Custom folder"
            else:
                output_badge.content.value = "Source folder"
            output_hint.value = _output_summary(files, custom_output_dir)
            detail_text.value = output_hint.value
            ml, mt = _model_status_label()
            model_badge.content.value = ml

        def update_ui():
            nonlocal is_running
            progress_bar.visible = is_running or progress_bar.value > 0
            if not files and not is_running:
                status_text.value = "Ready. Add image files to enable upscale."
            else:
                status_text.value = status_text.value or "Ready"
            run_btn.disabled = is_running or not files
            sync_meta()
            page.update()

        def open_output_folder(_=None):
            out_dir = _resolve_output_dir(files, custom_output_dir)
            if out_dir and out_dir.exists():
                os.startfile(str(out_dir))

        def use_source_folder(_=None):
            nonlocal custom_output_dir
            custom_output_dir = None
            persist_prefs()
            update_ui()

        def choose_output_folder(_=None):
            nonlocal custom_output_dir
            if folder_picker is None:
                return
            selected_dir = folder_picker.get_directory_path(
                dialog_title="Choose Output Folder",
                initial_directory=str(custom_output_dir) if custom_output_dir else None,
            )
            if selected_dir:
                custom_output_dir = Path(selected_dir)
                persist_prefs()
                update_ui()

        def on_clear(e):
            nonlocal files, is_running
            if is_running:
                return
            files = []
            log_box.value = ""
            status_text.value = "Ready"
            progress_bar.visible = False
            refresh_files()
            update_ui()

        def append_log(text: str):
            current = log_box.value or ""
            log_box.value = (current + text.strip() + "\n")[-4000:]
            page.update()

        def on_download_models(e):
            nonlocal is_running
            if is_running:
                return
            status_text.value = "Downloading model weights..."
            progress_bar.visible = True
            progress_bar.value = None
            page.update()

            def worker():
                nonlocal is_running
                script = Path(__file__).resolve().parents[2] / "setup" / "download_models.py"
                proc = subprocess.run(
                    [sys.executable, str(script), "--upscale"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                progress_bar.visible = False
                status_text.value = "Model download complete." if proc.returncode == 0 else "Model download failed."
                append_log((proc.stdout or "") + (proc.stderr or ""))
                refresh_files()
                update_ui()

            threading.Thread(target=worker, daemon=True).start()

        def on_start(e):
            nonlocal is_running, current_process
            if is_running or not files:
                return
            is_running = True
            run_btn.disabled = True
            progress_bar.visible = True
            progress_bar.value = 0
            log_box.value = ""
            status_text.value = "Preparing upscale job..."
            page.update()

            def worker():
                nonlocal is_running, current_process
                args = [str(path) for path in files]
                scale_value = scale_group.value or "4"
                args.extend(["--scale", scale_value])
                if face_checkbox.value:
                    args.append("--face-enhance")
                if tile_checkbox.value:
                    args.extend(["--tile", "512"])
                if custom_output_dir:
                    args.extend(["--output", str(custom_output_dir)])

                process = start_ai_script("upscale.py", *args)
                current_process = process
                completed = 0
                total = max(len(files), 1)
                for line in process.stdout:
                    line = line.rstrip()
                    if not line:
                        continue
                    append_log(line)
                    if line.startswith("[") and "/" in line:
                        completed += 1
                        progress_bar.value = min(completed / total, 0.95)
                        status_text.value = line
                        page.update()
                process.wait()
                current_process = None
                is_running = False
                progress_bar.visible = False
                progress_bar.value = 1 if process.returncode == 0 else 0
                status_text.value = "Upscale complete." if process.returncode == 0 else "Upscale failed."
                update_ui()

            threading.Thread(target=worker, daemon=True).start()

        # ── buttons ──
        run_btn = apply_button_sizing(
            ft.ElevatedButton("Start Upscale", on_click=on_start, bgcolor=COLORS["accent"], color=COLORS["text"]),
            "primary",
        )
        open_output_btn = apply_button_sizing(ft.OutlinedButton("Open Output", on_click=open_output_folder), "compact")
        source_folder_btn = apply_button_sizing(ft.OutlinedButton("Source Folder", on_click=use_source_folder), "compact")
        choose_folder_btn = apply_button_sizing(ft.OutlinedButton("Choose Folder", on_click=choose_output_folder), "compact")
        clear_btn = apply_button_sizing(ft.OutlinedButton("Clear", on_click=on_clear), "compact")
        download_btn = apply_button_sizing(ft.OutlinedButton("Download Models", on_click=on_download_models), "compact")

        # ── initial state ──
        refresh_files()
        sync_meta()

        # ── layout ──
        header = compact_meta_strip(
            "AI Image Upscaler",
            badges=[queue_badge, model_badge, output_badge],
        )
        files_card = section_card("Source Images", ft.Container(content=file_list, height=200))
        log_card = section_card("Run Log", log_box)
        settings_card = section_card(
            "Upscale Settings",
            ft.Column(
                [
                    ft.Text("Scale", size=13, color=COLORS["text_muted"]),
                    scale_group,
                    ft.Divider(height=1, color=COLORS["line"]),
                    ft.Text("Options", size=13, color=COLORS["text_muted"]),
                    face_checkbox,
                    tile_checkbox,
                    ft.Divider(height=1, color=COLORS["line"]),
                    ft.Row([download_btn], wrap=True),
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
                        integrated_title_bar(page, "AI Image Upscaler"),
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
                                            ft.Column([files_card, log_card], expand=3),
                                            ft.Column([settings_card], expand=2),
                                        ],
                                    ),
                                    action_bar(
                                        status=ft.Column([status_text, detail_text], spacing=2, tight=True),
                                        progress=progress_bar,
                                        primary=run_btn,
                                        secondary=[source_folder_btn, choose_folder_btn, open_output_btn, clear_btn],
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
