from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import flet as ft

from contexthub.ui.flet.layout import action_bar, apply_button_sizing, toolbar_row
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
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


class UpscaleFletApp:
    def __init__(self, initial_targets: list[str] | None = None):
        self.files = _collect_images(initial_targets)
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        self.current_process = None
        self.is_running = False
        self.page: ft.Page | None = None
        self.file_picker: ft.FilePicker | None = None

    def main(self, page: ft.Page):
        self.page = page
        configure_page(page, "AI Image Upscaler", window_profile="form")
        if not self.capture_mode:
            self.file_picker = ft.FilePicker(on_result=self.on_file_result)
            page.overlay.append(self.file_picker)

        self.file_count = ft.Text("", color=COLORS["text_muted"])
        self.output_hint = ft.Text("", color=COLORS["text_muted"])
        self.files_column = ft.ListView(spacing=SPACING["xs"], auto_scroll=False)
        self.status_text = ft.Text("Ready", color=COLORS["text_muted"])
        self.progress = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.log_box = ft.TextField(
            value="",
            multiline=True,
            read_only=True,
            min_lines=5,
            max_lines=8,
            border_radius=RADII["md"],
            bgcolor=COLORS["surface_alt"],
            border_color=COLORS["line"],
        )
        self.scale_group = ft.RadioGroup(
            value="4",
            content=ft.Row(
                controls=[
                    ft.Radio(value="2", label="2x"),
                    ft.Radio(value="4", label="4x"),
                ],
                spacing=SPACING["md"],
            ),
        )
        self.face_checkbox = ft.Checkbox(label="Face Enhance (GFPGAN)", value=False)
        self.tile_checkbox = ft.Checkbox(label="Use Tiling for low VRAM", value=False)
        self.model_status = ft.Text(self._model_status_label(), color=COLORS["text_muted"])
        self.run_button = apply_button_sizing(
            ft.ElevatedButton(
                "Start Upscale",
                on_click=self.on_start,
                bgcolor=COLORS["accent"],
                color="#FFFFFF",
            ),
            "primary",
        )

        page.add(
            ft.Container(
                expand=True,
                padding=ft.padding.all(SPACING["xl"]),
                content=ft.Column(
                    expand=True,
                    controls=[
                        self._build_header(),
                        ft.Row(
                            expand=True,
                            spacing=SPACING["md"],
                            controls=[
                                ft.Column(
                                    expand=3,
                                    controls=[
                                        self._build_files_card(),
                                        self._build_log_card(),
                                    ],
                                ),
                                ft.Column(
                                    expand=2,
                                    controls=[
                                        self._build_settings_card(),
                                        self._build_model_card(),
                                    ],
                                ),
                            ],
                        ),
                        action_bar(
                            status=self.status_text,
                            progress=self.progress,
                            primary=self.run_button,
                            secondary=[
                                ft.OutlinedButton("Open Folder", on_click=lambda e: self.open_output_folder()),
                                ft.OutlinedButton("Clear", on_click=self.on_clear),
                            ],
                        ),
                    ],
                ),
            )
        )
        self.refresh_files()

    def _build_header(self) -> ft.Container:
        return ft.Container(
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            padding=SPACING["lg"],
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Text("AI Image Upscaler", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Text("Load one or more images, pick 2x or 4x, and run ESRGAN in the RTX environment.", color=COLORS["text_muted"]),
                    ft.Row([self.file_count, self.output_hint], wrap=True, spacing=SPACING["md"]),
                ],
            ),
        )

    def _build_files_card(self) -> ft.Container:
        return ft.Container(
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            padding=SPACING["md"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[
                    toolbar_row(
                        ft.Text("Source Images", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                        apply_button_sizing(ft.OutlinedButton("Add Images", icon=ft.Icons.ADD_PHOTO_ALTERNATE, on_click=self.on_pick_files), "toolbar"),
                    ),
                    ft.Container(
                        height=180,
                        padding=SPACING["sm"],
                        bgcolor=COLORS["surface_alt"],
                        border_radius=RADII["md"],
                        border=ft.border.all(1, COLORS["line"]),
                        content=self.files_column,
                    ),
                ]
            ),
        )

    def _build_settings_card(self) -> ft.Container:
        return ft.Container(
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            padding=SPACING["md"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[
                    ft.Text("Upscale Settings", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Column(
                        controls=[
                            ft.Column([ft.Text("Scale", color=COLORS["text_muted"]), self.scale_group], spacing=6),
                            ft.Column(
                                [
                                    ft.Text("Options", color=COLORS["text_muted"]),
                                    self.face_checkbox,
                                    self.tile_checkbox,
                                    ft.Text("Output files are saved next to the original image.", size=12, color=COLORS["text_muted"]),
                                ],
                                spacing=6,
                                expand=True,
                            ),
                        ],
                        spacing=SPACING["md"],
                    ),
                ]
            ),
        )

    def _build_model_card(self) -> ft.Container:
        return ft.Container(
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            padding=SPACING["md"],
            content=ft.Column(
                controls=[
                    ft.Text("Model Status", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    self.model_status,
                    ft.Row(
                        wrap=True,
                        controls=[
                            apply_button_sizing(ft.OutlinedButton("Download Models", on_click=self.on_download_models), "toolbar"),
                            ft.Text("RealESRGAN_x4plus and GFPGAN weights are checked in the shared AI model cache.", size=12, color=COLORS["text_muted"]),
                        ],
                    ),
                ]
            ),
        )

    def _build_log_card(self) -> ft.Container:
        return ft.Container(
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            padding=SPACING["md"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[
                    ft.Text("Run Log", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    self.log_box,
                ]
            ),
        )

    def _model_status_label(self) -> str:
        model = paths.REALESRGAN_DIR / "RealESRGAN_x4plus.pth"
        gfpgan = paths.REALESRGAN_DIR / "GFPGANv1.4.pth"
        if model.exists() and gfpgan.exists():
            return "RealESRGAN and GFPGAN weights are ready."
        if model.exists():
            return "RealESRGAN ready. GFPGAN will be downloaded if face enhance is used."
        return "Model weights are missing. Download before the first upscale run."

    def refresh_files(self):
        self.files_column.controls.clear()
        if not self.files:
            self.files_column.controls.append(ft.Text("No images loaded yet.", color=COLORS["text_muted"]))
        for item in self.files[:6]:
            self.files_column.controls.append(
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=COLORS["text_muted"]),
                        ft.Text(item.name, expand=True, color=COLORS["text"]),
                        ft.Text(item.suffix.lower(), color=COLORS["text_muted"]),
                    ]
                )
            )
        if len(self.files) > 6:
            self.files_column.controls.append(ft.Text(f"... +{len(self.files) - 6} more", color=COLORS["text_muted"]))
        self.file_count.value = f"Images: {len(self.files)}"
        self.output_hint.value = "Output: source folder"
        self.model_status.value = self._model_status_label()
        self.run_button.disabled = self.is_running or not self.files
        if self.page:
            self.page.update()

    def append_log(self, text: str):
        current = self.log_box.value or ""
        self.log_box.value = (current + text.strip() + "\n")[-4000:]
        if self.page:
            self.page.update()

    def on_pick_files(self, e):
        if self.capture_mode or self.file_picker is None:
            return
        self.file_picker.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE)

    def on_file_result(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        merged = self.files + [Path(item.path) for item in e.files if item.path]
        self.files = _collect_images([str(path) for path in merged])
        self.refresh_files()

    def on_clear(self, e):
        if self.is_running:
            return
        self.files = []
        self.log_box.value = ""
        self.status_text.value = "Ready"
        self.progress.visible = False
        self.refresh_files()

    def on_download_models(self, e):
        if self.is_running:
            return
        self.status_text.value = "Downloading model weights..."
        self.progress.visible = True
        self.progress.value = None
        self.page.update()

        def worker():
            script = Path(__file__).resolve().parents[2] / "setup" / "download_models.py"
            proc = subprocess.run(
                [sys.executable, str(script), "--upscale"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.progress.visible = False
            self.status_text.value = "Model download complete." if proc.returncode == 0 else "Model download failed."
            self.append_log((proc.stdout or "") + (proc.stderr or ""))
            self.refresh_files()

        threading.Thread(target=worker, daemon=True).start()

    def on_start(self, e):
        if self.is_running or not self.files:
            return
        self.is_running = True
        self.run_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0
        self.log_box.value = ""
        self.status_text.value = "Preparing upscale job..."
        self.page.update()

        def worker():
            args = [str(path) for path in self.files]
            scale_value = self.scale_group.value or "4"
            args.extend(["--scale", scale_value])
            if self.face_checkbox.value:
                args.append("--face-enhance")
            if self.tile_checkbox.value:
                args.extend(["--tile", "512"])

            process = start_ai_script("upscale.py", *args)
            self.current_process = process
            completed = 0
            total = max(len(self.files), 1)
            for line in process.stdout:
                line = line.rstrip()
                if not line:
                    continue
                self.append_log(line)
                if line.startswith("[") and "/" in line:
                    completed += 1
                    self.progress.value = min(completed / total, 0.95)
                    self.status_text.value = line
                    self.page.update()
            process.wait()
            self.current_process = None
            self.is_running = False
            self.progress.visible = False
            self.progress.value = 1 if process.returncode == 0 else 0
            self.status_text.value = "Upscale complete." if process.returncode == 0 else "Upscale failed."
            self.refresh_files()

        threading.Thread(target=worker, daemon=True).start()

    def open_output_folder(self):
        if not self.files:
            return
        try:
            os.startfile(self.files[0].parent)
        except Exception as exc:
            self.status_text.value = f"Could not open folder: {exc}"
            self.page.update()


def open_upscale_flet(targets: list[str] | None = None):
    app = UpscaleFletApp(targets)
    ft.app(target=app.main)
