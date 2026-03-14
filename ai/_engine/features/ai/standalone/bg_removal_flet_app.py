from __future__ import annotations

import os
import threading
from pathlib import Path

import flet as ft

from contexthub.ui.flet.layout import action_bar, apply_button_sizing, toolbar_row
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
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


class BackgroundRemovalFletApp:
    def __init__(self, initial_targets: list[str] | None = None):
        self.files = _collect_images(initial_targets)
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        self.page: ft.Page | None = None
        self.file_picker: ft.FilePicker | None = None
        self.is_running = False

    def main(self, page: ft.Page):
        self.page = page
        configure_page(page, "AI Background Removal", window_profile="form")
        if not self.capture_mode:
            self.file_picker = ft.FilePicker(on_result=self.on_file_result)
            page.overlay.append(self.file_picker)

        self.file_count = ft.Text("", color=COLORS["text_muted"])
        self.model_note = ft.Text("", color=COLORS["text_muted"])
        self.files_column = ft.ListView(spacing=SPACING["xs"], auto_scroll=False)
        self.status_text = ft.Text("Ready", color=COLORS["text_muted"])
        self.progress = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.log_box = ft.TextField(
            value="",
            multiline=True,
            read_only=True,
            min_lines=4,
            max_lines=7,
            border_radius=RADII["md"],
            bgcolor=COLORS["surface_alt"],
            border_color=COLORS["line"],
        )
        self.model_dropdown = ft.Dropdown(
            label="Model",
            value="birefnet",
            width=220,
            options=[
                ft.dropdown.Option("birefnet"),
                ft.dropdown.Option("inspyrenet"),
                ft.dropdown.Option("rmbg"),
            ],
            on_select=lambda e: self.refresh_notes(),
        )
        self.transparency_checkbox = ft.Checkbox(label="Transparent PNG output", value=True)
        self.postprocess_dropdown = ft.Dropdown(
            label="Post-process",
            value="none",
            width=220,
            options=[
                ft.dropdown.Option("none"),
                ft.dropdown.Option("smooth"),
                ft.dropdown.Option("sharpen"),
                ft.dropdown.Option("feather"),
            ],
        )
        self.run_button = apply_button_sizing(
            ft.ElevatedButton(
                "Start Background Removal",
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
        self.refresh_notes()

    def _build_header(self) -> ft.Container:
        return ft.Container(
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            padding=SPACING["lg"],
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Text("AI Background Removal", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Text("Choose a model, keep transparency when needed, and process the current image batch.", color=COLORS["text_muted"]),
                    self.file_count,
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
                        ft.Text("Target Images", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
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
                    ft.Text("Removal Settings", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Column(
                        controls=[
                            self.model_dropdown,
                            self.postprocess_dropdown,
                            self.transparency_checkbox,
                        ],
                        spacing=SPACING["md"],
                    ),
                    self.model_note,
                    ft.Text("Outputs are saved next to the source image with a removed-background suffix.", size=12, color=COLORS["text_muted"]),
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

    def refresh_notes(self):
        model = self.model_dropdown.value if hasattr(self, "model_dropdown") else "birefnet"
        notes = {
            "birefnet": "Highest quality default. Downloads from Hugging Face on first use.",
            "inspyrenet": "Fast fallback for lighter runs.",
            "rmbg": "Requires Hugging Face approval and token access for RMBG-2.0.",
        }
        self.model_note.value = notes.get(model, "")
        if self.page:
            self.page.update()

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

    def on_start(self, e):
        if self.is_running or not self.files:
            return
        self.is_running = True
        self.run_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0
        self.log_box.value = ""
        self.status_text.value = "Preparing background removal..."
        self.page.update()

        def worker():
            total = max(len(self.files), 1)
            errors: list[str] = []
            for index, path in enumerate(self.files, start=1):
                args = [str(path), "--model", self.model_dropdown.value]
                if not self.transparency_checkbox.value:
                    args.append("--no-transparency")
                if self.postprocess_dropdown.value != "none":
                    args.extend(["--postprocess", self.postprocess_dropdown.value])
                self.status_text.value = f"Processing {index}/{total}: {path.name}"
                self.progress.value = (index - 1) / total
                self.page.update()
                process = start_ai_script("bg_removal.py", *args)
                stdout, _ = process.communicate()
                output = (stdout or "").strip()
                if output:
                    self.append_log(output)
                if process.returncode != 0:
                    errors.append(path.name)
            self.is_running = False
            self.progress.visible = False
            self.progress.value = 1 if not errors else 0
            self.status_text.value = "Background removal complete." if not errors else f"Finished with errors: {len(errors)} file(s)."
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


def open_bg_removal_flet(targets: list[str] | None = None):
    app = BackgroundRemovalFletApp(targets)
    ft.app(target=app.main)
