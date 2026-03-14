from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

import flet as ft

from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from utils.external_tools import get_blender, get_mayo_conv, get_mayo_viewer

from features.mesh.mesh_service import MeshService
from features.mesh.mesh_state import MeshAppState


MODE_LABELS = {
    "convert": "Mesh Convert",
    "cad": "CAD to OBJ",
    "bake": "Blender Bake",
    "lod": "Auto LOD Generator",
    "mayo": "Open with Mayo",
}

MODE_NOTES = {
    "convert": "Convert source meshes into a standard target format for downstream DCC tools.",
    "cad": "Send CAD files through the Mayo conversion tool and export clean OBJ outputs.",
    "bake": "Prepare Blender-based baking tasks from the current source mesh set.",
    "lod": "Generate lower-detail variants from source meshes for runtime use.",
    "mayo": "Open selected CAD assets in the Mayo viewer for quick inspection.",
}


def _resolve_dependency(mode: str) -> tuple[str, bool, str]:
    resolver: Callable[[], str] | None = None
    label = "No extra dependency required for the default capture flow."
    if mode in {"convert", "bake"}:
        resolver = get_blender
        label = "Blender is required."
    elif mode == "cad":
        resolver = get_mayo_conv
        label = "Mayo Converter is required."
    elif mode == "mayo":
        resolver = get_mayo_viewer
        label = "Mayo Viewer is required."

    if resolver is None:
        return label, True, "Ready"

    try:
        return label, True, resolver()
    except Exception as exc:
        return label, False, str(exc)


def start_app(targets: list[str] | None = None, mode: str = "convert"):
    def main(page: ft.Page):
        state = MeshAppState(mode=mode)
        service = MeshService()
        if targets:
            state.input_paths = [Path(path) for path in targets if Path(path).exists()]

        configure_page(page, MODE_LABELS.get(mode, "Mesh Tool"), window_profile="wide")
        page.bgcolor = COLORS["app_bg"]

        dep_label, dep_ready, dep_detail = _resolve_dependency(mode)
        status_text = ft.Text("Ready", color=COLORS["text_muted"], size=12)
        progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])
        file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE)

        def rebuild_files():
            file_list.controls = []
            for src in state.input_paths:
                file_list.controls.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
                        border_radius=RADII["sm"],
                        bgcolor=COLORS["surface_alt"],
                        border=ft.border.all(1, COLORS["line"]),
                        content=ft.Row(
                            [ft.Icon(ft.Icons.DATA_OBJECT, size=16, color=COLORS["text_muted"]), ft.Text(src.name, size=12)],
                            spacing=SPACING["sm"],
                        ),
                    )
                )
            if not file_list.controls:
                file_list.controls.append(
                    ft.Container(
                        padding=SPACING["md"],
                        border_radius=RADII["sm"],
                        border=ft.border.all(1, COLORS["line"]),
                        bgcolor=COLORS["surface_alt"],
                        content=ft.Text(
                            "No input files yet. Launch this app from the context menu on one or more source assets.",
                            color=COLORS["text_muted"],
                        ),
                    )
                )

        def update_ui():
            progress_bar.visible = state.is_processing or state.progress > 0
            progress_bar.value = state.progress
            status_text.value = state.status_text
            start_btn.disabled = state.is_processing or not state.input_paths or not dep_ready
            page.update()

        def on_progress(current, total, filename):
            state.progress = 0 if total == 0 else current / total
            state.status_text = f"Processing {current + 1}/{total}: {filename}"
            page.run_thread(update_ui)

        def on_complete(success, total, errors, last_path):
            state.is_processing = False
            state.progress = 1.0 if total else 0
            state.status_text = f"Finished {success}/{total}"
            state.last_output = last_path
            page.run_thread(update_ui)

            message = f"Processed {success}/{total} items."
            if errors:
                message += "\n\n" + "\n".join(errors[:5])
            dialog = ft.AlertDialog(
                title=ft.Text("Task Complete"),
                content=ft.Text(message),
                actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))],
            )
            page.open(dialog)

        def on_start(e: ft.ControlEvent):
            if not dep_ready:
                state.status_text = "Required dependency is not configured."
                update_ui()
                return
            if not state.input_paths:
                return
            state.is_processing = True
            state.progress = 0
            state.status_text = "Preparing task..."
            update_ui()
            threading.Thread(
                target=service.execute_mesh_task,
                args=(state.mode, state.input_paths, on_progress, on_complete),
                kwargs={"format": "OBJ", "ratio": state.lod_ratio},
                daemon=True,
            ).start()

        summary = ft.Container(
            padding=SPACING["lg"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[
                    ft.Text(MODE_LABELS.get(mode, "Mesh Tool"), size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(MODE_NOTES.get(mode, ""), color=COLORS["text_muted"]),
                    ft.Text(f"Inputs: {len(state.input_paths)}", color=COLORS["text_muted"]),
                ],
            ),
        )

        if dep_ready:
            dep_controls = [
                ft.Text(dep_label, color=COLORS["text"]),
                ft.Text(dep_detail, size=12, color=COLORS["text_muted"]),
            ]
        else:
            dep_controls = [
                ft.Text(dep_label, color=COLORS["warning"], weight=ft.FontWeight.BOLD),
                ft.Text(dep_detail, size=12, color=COLORS["text_muted"]),
                ft.Text(
                    "Set the path in shared settings or copy the tool into the local Shared runtime tools folder.",
                    size=12,
                    color=COLORS["text_muted"],
                ),
            ]

        dependency_card = ft.Container(
            padding=SPACING["md"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[ft.Text("Dependency Status", size=16, weight=ft.FontWeight.BOLD), *dep_controls],
            ),
        )

        settings_text = "Mode-specific options will appear here next."
        if mode == "lod":
            settings_text = f"LOD Ratio: {state.lod_ratio:.2f}"
        settings_card = ft.Container(
            padding=SPACING["md"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[
                    ft.Text("Task Settings", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text("Default validated capture preset is active.", color=COLORS["text_muted"]),
                    ft.Text("Output Format: OBJ", color=COLORS["text"]),
                    ft.Text(settings_text, color=COLORS["text_muted"] if mode != "lod" else COLORS["text"]),
                ],
            ),
        )

        files_card = ft.Container(
            padding=SPACING["md"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[
                    ft.Text("Input Files", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(content=file_list, height=300),
                ],
            ),
        )

        start_btn = ft.ElevatedButton("Start Task", on_click=on_start, bgcolor=COLORS["accent"], color=COLORS["text"])
        close_btn = ft.OutlinedButton("Close", on_click=lambda e: page.window_close())
        apply_button_sizing(start_btn, "primary")
        apply_button_sizing(close_btn, "compact")

        rebuild_files()
        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                padding=SPACING["lg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["md"],
                    controls=[
                        summary,
                        ft.Row(
                            expand=True,
                            spacing=SPACING["md"],
                            controls=[
                                ft.Container(expand=3, content=files_card),
                                ft.Column(expand=2, spacing=SPACING["md"], controls=[dependency_card, settings_card]),
                            ],
                        ),
                        action_bar(status=status_text, progress=progress_bar, primary=start_btn, secondary=[close_btn]),
                    ],
                ),
            )
        )
        update_ui()

    ft.app(target=main)
