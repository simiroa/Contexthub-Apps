"""Mesh conversion tool Flet UI.

Centralized two-column layout aligned with image-category shell.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import List

import flet as ft

from contexthub.ui.flet.layout import (
    action_bar,
    apply_button_sizing,
    compact_meta_strip,
    integrated_title_bar,
    section_card,
    status_badge,
)
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.window import reveal_desktop_window
from utils.i18n import t

from .mesh_service import MeshService
from .mesh_state import MeshAppState


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if not value or value == key else value


MODE_LABELS = {
    "convert": "Mesh Convert",
    "cad": "CAD to OBJ",
    "bake": "Mesh Bake",
    "extract": "Extract Textures",
    "lod": "Auto LOD",
    "mayo": "Open with Mayo",
}


MODE_NOTES = {
    "convert": "Convert 3D mesh formats using Blender.",
    "cad": "Export CAD-compatible formats using Mayo converter.",
    "bake": "Bake textures from mesh geometry to textures.",
    "extract": "Extract embedded textures from mesh containers.",
    "lod": "Generate lower detail levels.",
    "mayo": "Open selected source files in Mayo viewer.",
}


def _numeric_field(label: str, default: str, width: int = 130) -> ft.TextField:
    return ft.TextField(label=label, value=default, width=width, dense=True, input_filter=ft.NumbersOnlyInputFilter())


PRIMARY_LABELS = {
    "convert": "Convert",
    "cad": "Export",
    "bake": "Bake",
    "extract": "Extract",
    "lod": "LOD",
    "mayo": "Open",
}


def _format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def _allowed_extensions_for_mode(mode: str) -> set[str]:
    if mode == "cad":
        return {".step", ".stp", ".iges", ".igs", ".brep", ".stl", ".obj"}
    if mode == "extract":
        return {".fbx", ".glb", ".gltf"}
    if mode == "mayo":
        return {".step", ".stp", ".iges", ".igs", ".brep", ".stl", ".obj", ".fbx", ".glb", ".gltf"}
    return {".fbx", ".obj", ".glb", ".gltf", ".usd", ".usdc", ".stl", ".ply"}


def _supports_path(mode: str, path: Path) -> tuple[bool, str]:
    if path.suffix.lower() not in _allowed_extensions_for_mode(mode):
        return False, "Blocked"
    if mode == "extract" and path.suffix.lower() not in {".fbx", ".glb", ".gltf"}:
        return False, "No textures"
    return True, "Ready"


class MeshFletApp:
    def __init__(self, initial_files: List[str], mode: str = "convert"):
        self.service = MeshService()
        self.state = MeshAppState(mode=mode, input_paths=[Path(f) for f in initial_files if Path(f).exists()])
        self.capture_mode = False

    async def main(self, page: ft.Page):
        self.page = page
        title = MODE_LABELS.get(self.state.mode, "Mesh Tool")
        configure_page(page, title, window_profile="two_pane")
        page.bgcolor = COLORS["app_bg"]
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"

        if not self.capture_mode:
            self.file_picker = ft.FilePicker(on_result=self.on_file_result)
            page.overlay.append(self.file_picker)
        else:
            self.file_picker = None

        self.file_list = ft.Column(spacing=SPACING["xs"], scroll=ft.ScrollMode.AUTO)
        self.file_body = ft.Container()
        self.file_empty = ft.Container()
        self.file_header = ft.Container(
            padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=6),
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["line"])),
            content=ft.Row(
                [
                    ft.Text("Name", size=10, color=COLORS["text_soft"], expand=True),
                    ft.Text("Size", size=10, color=COLORS["text_soft"], width=76, text_align=ft.TextAlign.RIGHT),
                    ft.Text("Status", size=10, color=COLORS["text_soft"], width=72, text_align=ft.TextAlign.RIGHT),
                ],
                spacing=SPACING["sm"],
            ),
        )
        self.queue_badge = status_badge("0 files", "muted")
        self.mode_badge = status_badge(title, "accent")
        self.format_badge = status_badge("OBJ", "muted")
        self.dep_badge = status_badge("Tool", "muted")
        self.selection_badge = status_badge("0 ready", "muted")

        self.status_text = ft.Text(_tr("common.ready", "Ready"), size=12, color=COLORS["text_muted"])
        self.detail_text = ft.Text("", size=11, color=COLORS["text_soft"], no_wrap=True)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"], bgcolor=COLORS["line"])

        self.dd_format = ft.Dropdown(
            label=_tr("mesh_convert.output_format", "Output Format"),
            options=[ft.dropdown.Option(v) for v in ["OBJ", "FBX", "GLB", "USD", "PLY", "STL"]],
            value=self.state.output_format,
            on_select=self.on_param_change,
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
        )

        self.chk_subfolder = ft.Checkbox(
            label=_tr("mesh_convert.convert_to_subfolder", "Save output to subfolder"),
            value=self.state.convert_to_subfolder,
            on_change=self.on_param_change,
            scale=0.95,
        )

        self.slider_ratio = ft.Slider(
            value=self.state.lod_ratio,
            min=0.1,
            max=1.0,
            divisions=18,
            label="{value}x",
            on_change=self.on_param_change,
            active_color=COLORS["accent"],
            thumb_color=COLORS["accent"],
            disabled=self.state.mode != "lod",
            expand=True,
        )
        self.lbl_ratio = ft.Text(f"{self.state.lod_ratio:.2f}", size=11, color=COLORS["text_soft"])
        self.tf_lod_count = ft.TextField(
            label="LOD Count",
            value=str(self.state.lod_count),
            width=120,
            on_change=self.on_param_change,
            input_filter=ft.NumbersOnlyInputFilter(),
            dense=True,
        )

        self.chk_preserve_uv = ft.Checkbox(label="Preserve UV", value=self.state.preserve_uv, on_change=self.on_param_change, scale=0.95)
        self.chk_preserve_normal = ft.Checkbox(
            label="Preserve Normal", value=self.state.preserve_normal, on_change=self.on_param_change, scale=0.95
        )
        self.chk_preserve_boundary = ft.Checkbox(
            label="Preserve Boundary", value=self.state.preserve_boundary, on_change=self.on_param_change, scale=0.95
        )

        self.tf_target_scale = _numeric_field("Target Scale", str(self.state.target_scale), 120)
        self.tf_target_scale.input_filter = None
        self.tf_target_scale.on_change = self.on_param_change
        self.tf_target_faces = _numeric_field("Target Faces", str(self.state.target_faces), 140)
        self.tf_target_faces.on_change = self.on_param_change
        self.tf_bake_size = _numeric_field("Bake Size", str(self.state.bake_size), 130)
        self.tf_bake_size.on_change = self.on_param_change
        self.tf_bake_ray = _numeric_field("Ray Distance", str(self.state.bake_ray_dist), 130)
        self.tf_bake_ray.input_filter = None
        self.tf_bake_ray.on_change = self.on_param_change
        self.tf_bake_margin = _numeric_field("Margin", str(self.state.bake_margin), 110)
        self.tf_bake_margin.on_change = self.on_param_change

        self.chk_bake_diffuse = ft.Checkbox(label="Diffuse", value=self.state.bake_diffuse, on_change=self.on_param_change, scale=0.95)
        self.chk_bake_orm = ft.Checkbox(label="ORM Packed", value=self.state.bake_orm_pack, on_change=self.on_param_change, scale=0.95)
        self.chk_bake_flip = ft.Checkbox(label="Flip Green", value=self.state.bake_flip_green, on_change=self.on_param_change, scale=0.95)

        self.start_btn = ft.ElevatedButton(PRIMARY_LABELS.get(self.state.mode, "Start"), icon=ft.Icons.PLAY_ARROW, bgcolor=COLORS["accent"], color=COLORS["text"])
        self.start_btn = apply_button_sizing(self.start_btn, "primary")
        self.start_btn.on_click = self.on_start
        self.source_btn = apply_button_sizing(ft.IconButton(icon=ft.Icons.FOLDER_OPEN, tooltip="Open source folder", on_click=self.on_open_source_folder), "compact")
        self.open_btn = apply_button_sizing(ft.IconButton(icon=ft.Icons.OPEN_IN_NEW, tooltip="Open output folder", on_click=self.on_open_output), "compact")
        self.close_btn = apply_button_sizing(ft.IconButton(icon=ft.Icons.CLOSE, tooltip="Close", on_click=self.on_close), "compact")
        self.add_btn = apply_button_sizing(ft.IconButton(icon=ft.Icons.ADD, tooltip="Add files", on_click=self.on_pick_files), "compact")
        self.remove_btn = apply_button_sizing(ft.IconButton(icon=ft.Icons.REMOVE, tooltip="Remove selected", on_click=self.on_remove_selected), "compact")
        self.clear_btn = apply_button_sizing(ft.IconButton(icon=ft.Icons.CLEAR_ALL, tooltip="Clear all", on_click=self.on_clear_files), "compact")

        self.files_card = section_card(
            _tr("mesh_convert.files", "Input Files"),
            ft.Column(
                [
                    self.file_header,
                    self.file_empty,
                    self.file_body,
                ],
                spacing=0,
            ),
            actions=[self.add_btn, self.remove_btn, self.clear_btn],
        )
        self.settings_card = section_card(
            _tr("mesh_convert.settings", "Task Settings"),
            ft.Column(
                controls=[
                    ft.Text(MODE_NOTES.get(self.state.mode, ""), size=11, color=COLORS["text_muted"]),
                    self._build_settings_panel(),
                ],
                spacing=SPACING["sm"],
            ),
        )

        header = compact_meta_strip(
            title,
            description=MODE_NOTES.get(self.state.mode, ""),
            badges=[self.mode_badge, self.queue_badge, self.selection_badge, self.format_badge, self.dep_badge],
        )

        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                padding=SPACING["lg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["md"],
                    controls=[
                        integrated_title_bar(page, title),
                        ft.Container(
                            expand=True,
                            padding=ft.padding.all(SPACING["sm"]),
                            content=ft.Column(
                                expand=True,
                                spacing=SPACING["sm"],
                                controls=[
                                    header,
                                    ft.Row(
                                        spacing=SPACING["md"],
                                        vertical_alignment=ft.CrossAxisAlignment.START,
                                        controls=[
                                            ft.Column([self.files_card], expand=3),
                                            ft.Column([self.settings_card], expand=2),
                                        ],
                                    ),
                                    action_bar(
                                        status=ft.Column([self.status_text, self.detail_text], spacing=2, tight=True),
                                        progress=self.progress_bar,
                                        primary=self.start_btn,
                                        secondary=[self.source_btn, self.open_btn, self.close_btn],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            )
        )

        self.on_param_change(None)
        self._rebuild_file_list()
        self._update_dependency_hint()
        self._refresh_ui()
        await reveal_desktop_window(page)

    def _build_settings_panel(self) -> ft.Container:
        mode = self.state.mode
        base: list = []

        if mode in {"convert", "cad"}:
            base.extend([self.dd_format, self.chk_subfolder])
        elif mode == "bake":
            base.extend(
                [
                    self.tf_target_scale,
                    ft.Row([ft.Text("Target Faces"), self.tf_target_faces], spacing=SPACING["sm"]),
                    ft.Row([self.chk_preserve_uv, self.chk_preserve_normal, self.chk_preserve_boundary], spacing=SPACING["xs"]),
                    ft.Row([ft.Text("Bake Size"), self.tf_bake_size], spacing=SPACING["sm"]),
                    ft.Row([ft.Text("Ray Distance"), self.tf_bake_ray], spacing=SPACING["sm"]),
                    ft.Row([ft.Text("Margin"), self.tf_bake_margin], spacing=SPACING["sm"]),
                    ft.Row([self.chk_bake_diffuse, self.chk_bake_orm, self.chk_bake_flip], spacing=SPACING["xs"]),
                ]
            )
        elif mode == "lod":
            base.extend(
                [
                    ft.Row([ft.Text("LOD Ratio"), self.lbl_ratio, ft.Text(f"x{int(self.state.lod_ratio*100)}%")], spacing=SPACING["sm"]),
                    ft.Container(
                        content=self.slider_ratio,
                        border=ft.border.all(1, COLORS["line"]),
                        border_radius=RADII["sm"],
                        padding=SPACING["xs"],
                    ),
                    ft.Row([ft.Text("LOD Count"), self.tf_lod_count], spacing=SPACING["sm"]),
                    ft.Row([self.chk_preserve_uv, self.chk_preserve_normal, self.chk_preserve_boundary], spacing=SPACING["xs"]),
                ]
            )
        elif mode == "extract":
            base.append(ft.Text("Extract textures from supported mesh containers.", size=11, color=COLORS["text_muted"]))
        else:
            base.append(ft.Text("No extra options for Mayo mode.", size=11, color=COLORS["text_muted"]))

        return ft.Container(
            content=ft.Column(controls=base, spacing=SPACING["sm"], expand=True),
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            padding=SPACING["md"],
        )

    def _update_dependency_hint(self):
        if self.state.mode in {"mayo", "extract"}:
            self.dep_badge.content.value = "Mayo + Blender"
        elif self.state.mode == "cad":
            self.dep_badge.content.value = "Mayo"
        elif self.state.mode in {"convert", "bake", "lod"}:
            self.dep_badge.content.value = "Blender"
        else:
            self.dep_badge.content.value = "Tools"

    def _normalize_int(self, value: str | None, fallback: int) -> int:
        try:
            return max(1, int(value or str(fallback)))
        except Exception:
            return fallback

    def _normalize_float(self, value: str | None, fallback: float) -> float:
        try:
            return max(0.01, float(value or str(fallback)))
        except Exception:
            return fallback

    def _collect_options(self) -> dict:
        options: dict = {
            "format": self.state.output_format,
            "convert_to_subfolder": self.state.convert_to_subfolder,
        }
        if self.state.mode == "bake":
            options.update(
                {
                    "maps": list(self.state.bake_maps),
                    "target_scale": self.state.target_scale,
                    "target_faces": self.state.target_faces,
                    "preserve_uv": self.state.preserve_uv,
                    "preserve_normal": self.state.preserve_normal,
                    "preserve_boundary": self.state.preserve_boundary,
                    "bake_size": self.state.bake_size,
                    "bake_ray_dist": self.state.bake_ray_dist,
                    "bake_margin": self.state.bake_margin,
                    "bake_flip_green": self.state.bake_flip_green,
                    "bake_diffuse": self.state.bake_diffuse,
                    "bake_orm_pack": self.state.bake_orm_pack,
                }
            )
        elif self.state.mode == "lod":
            options.update(
                {
                    "ratio": self.state.lod_ratio,
                    "lod_count": self.state.lod_count,
                    "preserve_uv": self.state.preserve_uv,
                    "preserve_normal": self.state.preserve_normal,
                    "preserve_boundary": self.state.preserve_boundary,
                }
            )
        return options

    def _eligible_paths(self) -> List[Path]:
        return [path for path in self.state.input_paths if _supports_path(self.state.mode, path)[0]]

    def _build_file_row(self, path: Path, index: int) -> ft.Container:
        is_ready, status = _supports_path(self.state.mode, path)
        is_selected = index == self.state.selected_index
        border_color = COLORS["accent"] if is_selected else COLORS["line"]
        bg_color = COLORS["surface"] if is_selected else COLORS["surface_alt"]
        status_color = COLORS.get("success", COLORS["accent"]) if is_ready else COLORS["warning"]
        icon_name = ft.Icons.CHECK_CIRCLE if is_ready else ft.Icons.ERROR_OUTLINE
        size_text = _format_size(path.stat().st_size) if path.exists() else "-"
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=10),
            bgcolor=bg_color,
            border=ft.border.all(1, border_color),
            border_radius=RADII["sm"],
            on_click=lambda _: self.on_select_file(index),
            content=ft.Row(
                [
                    ft.Icon(icon_name, size=16, color=status_color),
                    ft.Column(
                        [
                            ft.Text(path.name, size=12, color=COLORS["text"], no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(path.suffix.upper().lstrip("."), size=10, color=COLORS["text_soft"]),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Text(size_text, size=10, color=COLORS["text_soft"], width=76, text_align=ft.TextAlign.RIGHT),
                    ft.Text(status, size=10, color=status_color, width=72, text_align=ft.TextAlign.RIGHT),
                ],
                spacing=SPACING["sm"],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )

    def _rebuild_file_list(self):
        if self.state.input_paths:
            self.file_list.controls.clear()
            for index, path in enumerate(self.state.input_paths):
                self.file_list.controls.append(self._build_file_row(path, index))
            self.file_empty.visible = False
            self.file_body.height = 486
            self.file_body.bgcolor = COLORS["surface"]
            self.file_body.padding = None
            self.file_body.visible = True
            self.file_body.content = self.file_list
        else:
            self.file_body.visible = False
            self.file_empty.visible = True
            self.file_empty.padding = ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["md"])
            self.file_empty.content = ft.Container(
                bgcolor="transparent",
                content=ft.Column(
                    [
                        ft.Text("No input files yet.", size=12, color=COLORS["text"]),
                        ft.Text("Add files to populate the list with filename, size, and availability.", size=11, color=COLORS["text_soft"]),
                        ft.Text(
                            f"Supported: {', '.join(sorted(ext.lstrip('.') for ext in _allowed_extensions_for_mode(self.state.mode)))}",
                            size=10,
                            color=COLORS["text_soft"],
                        ),
                    ],
                    spacing=6,
                ),
            )
        self.queue_badge.content.value = f"{len(self.state.input_paths)} files"

    def _sync_mode_ui(self):
        self.dd_format.disabled = self.state.mode not in {"convert", "cad", "bake", "lod", "extract", "mayo"}
        self.chk_subfolder.disabled = self.state.mode not in {"convert", "cad", "bake", "lod", "extract"}
        self.slider_ratio.disabled = self.state.mode != "lod"
        self.tf_lod_count.disabled = self.state.mode != "lod"
        self.tf_target_scale.disabled = self.state.mode != "bake"
        self.tf_target_faces.disabled = self.state.mode != "bake"
        self.tf_bake_size.disabled = self.state.mode != "bake"
        self.tf_bake_ray.disabled = self.state.mode != "bake"
        self.tf_bake_margin.disabled = self.state.mode != "bake"
        self.chk_bake_diffuse.disabled = self.state.mode != "bake"
        self.chk_bake_orm.disabled = self.state.mode != "bake"
        self.chk_bake_flip.disabled = self.state.mode != "bake"
        self.chk_preserve_uv.disabled = self.state.mode not in {"bake", "lod"}
        self.chk_preserve_normal.disabled = self.state.mode not in {"bake", "lod"}
        self.chk_preserve_boundary.disabled = self.state.mode not in {"bake", "lod"}
        self.lbl_ratio.value = f"{self.state.lod_ratio:.2f}"

    def _refresh_ui(self):
        ready_count = len(self._eligible_paths())
        self.format_badge.content.value = self.state.output_format
        self.queue_badge.content.value = f"{len(self.state.input_paths)} files"
        self.selection_badge.content.value = f"{ready_count} ready"
        self.mode_badge.content.value = MODE_LABELS.get(self.state.mode, "Mesh Tool")
        self.status_text.value = self.state.status_text
        self.detail_text.value = self.state.error_message or (self.state.last_output.as_posix() if self.state.last_output else "")
        self.progress_bar.visible = self.state.is_processing
        self.progress_bar.value = self.state.progress
        self.start_btn.disabled = self.state.is_processing or ready_count == 0
        self.remove_btn.disabled = self.state.selected_index < 0 or self.state.selected_index >= len(self.state.input_paths)
        self.start_btn.text = (
            _tr("common.processing", "Processing...")
            if self.state.is_processing
            else PRIMARY_LABELS.get(self.state.mode, "Start")
        )
        self._sync_mode_ui()
        self.page.update()

    def _sync_options_to_state(self):
        self.state.output_format = self.dd_format.value or self.state.output_format
        self.state.convert_to_subfolder = bool(self.chk_subfolder.value)
        self.state.lod_ratio = float(self.slider_ratio.value)
        self.state.lod_count = self._normalize_int(self.tf_lod_count.value, self.state.lod_count)
        self.state.target_scale = self._normalize_float(self.tf_target_scale.value, self.state.target_scale)
        self.state.target_faces = self._normalize_int(self.tf_target_faces.value, self.state.target_faces)
        self.state.preserve_uv = bool(self.chk_preserve_uv.value)
        self.state.preserve_normal = bool(self.chk_preserve_normal.value)
        self.state.preserve_boundary = bool(self.chk_preserve_boundary.value)
        self.state.bake_size = self._normalize_int(self.tf_bake_size.value, self.state.bake_size)
        self.state.bake_ray_dist = self._normalize_float(self.tf_bake_ray.value, self.state.bake_ray_dist)
        self.state.bake_margin = self._normalize_int(self.tf_bake_margin.value, self.state.bake_margin)
        self.state.bake_flip_green = bool(self.chk_bake_flip.value)
        self.state.bake_diffuse = bool(self.chk_bake_diffuse.value)
        self.state.bake_orm_pack = bool(self.chk_bake_orm.value)
        maps: List[str] = []
        if self.chk_bake_diffuse.value:
            maps.append("Diffuse")
        if self.chk_bake_orm.value:
            maps.append("ORM")
        self.state.bake_maps = maps if maps else ["Diffuse", "Normal"]

    def on_param_change(self, _):
        if self.state.mode == "lod":
            self.lbl_ratio.value = f"{self.slider_ratio.value:.2f}"
        self._sync_options_to_state()
        self._rebuild_file_list()
        self._refresh_ui()
        self.page.update()

    def on_pick_files(self, _):
        if not self.file_picker:
            return
        self.file_picker.pick_files(
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=[ext.lstrip(".") for ext in sorted(_allowed_extensions_for_mode(self.state.mode))],
        )

    def on_file_result(self, e):
        if not e.files:
            return
        ext = _allowed_extensions_for_mode(self.state.mode)
        known = {str(p.resolve()) for p in self.state.input_paths}
        for f in e.files:
            p = Path(f.path)
            if not p.exists() or p.suffix.lower() not in ext:
                continue
            rp = str(p.resolve())
            if rp in known:
                continue
            self.state.input_paths.append(p)
            known.add(rp)
        if self.state.selected_index < 0 and self.state.input_paths:
            self.state.selected_index = 0
        self._rebuild_file_list()
        self._refresh_ui()
        self.page.update()

    def on_clear_files(self, _):
        self.state.input_paths.clear()
        self.state.selected_index = -1
        self._rebuild_file_list()
        self._refresh_ui()
        self.page.update()

    def on_select_file(self, index: int):
        self.state.selected_index = index
        path = self.state.input_paths[index]
        _, status = _supports_path(self.state.mode, path)
        self.state.error_message = f"{path.name} • {status}"
        self._rebuild_file_list()
        self._refresh_ui()

    def on_remove_selected(self, _):
        index = self.state.selected_index
        if index < 0 or index >= len(self.state.input_paths):
            return
        self.state.input_paths.pop(index)
        if not self.state.input_paths:
            self.state.selected_index = -1
        else:
            self.state.selected_index = min(index, len(self.state.input_paths) - 1)
        self._rebuild_file_list()
        self._refresh_ui()
        self.page.update()

    def on_open_source_folder(self, _):
        if not self.state.input_paths:
            return
        os.startfile(str(self.state.input_paths[0].parent))

    def on_open_output(self, _):
        if not self.state.last_output:
            return
        os.startfile(str(self.state.last_output.parent))

    def on_close(self, _):
        self.page.window_close()

    def on_start(self, _):
        run_paths = self._eligible_paths()
        if self.state.is_processing or not run_paths:
            return
        self._sync_options_to_state()
        self.state.is_processing = True
        self.state.progress = 0
        self.state.status_text = _tr("common.initializing", "Initializing...")
        blocked_count = len(self.state.input_paths) - len(run_paths)
        self.state.error_message = f"{blocked_count} blocked" if blocked_count else None
        self.state.last_output = None
        self._refresh_ui()
        threading.Thread(target=self._run_task, args=(run_paths, blocked_count), daemon=True).start()

    def _run_task(self, run_paths: List[Path], blocked_count: int):
        def on_progress(current: int, total: int, filename: str):
            self.state.progress = current / total if total else 0
            self.state.status_text = f"{current}/{total}"
            self.state.error_message = filename
            self.page.run_thread(self._refresh_ui)

        def on_complete(success: int, total: int, errors: List[str], last_path: Path | None):
            self.state.is_processing = False
            self.state.progress = 1.0 if total and not errors else self.state.progress
            if blocked_count:
                errors = [f"{blocked_count} file(s) blocked by current mode."] + errors
            if errors:
                self.state.status_text = f"{len(errors)} errors."
                self.state.error_message = "; ".join(errors[:2])
            else:
                self.state.status_text = f"{success}/{total} " + _tr("common.completed", "completed.")
                self.state.error_message = _tr("common.done", "Done.")
            self.state.last_output = last_path
            self.page.run_thread(lambda: self._show_complete_dialog(success, total, errors))
            self.page.run_thread(self._refresh_ui)

        options = self._collect_options()
        try:
            self.service.execute_mesh_task(
                self.state.mode,
                run_paths,
                on_progress=on_progress,
                on_complete=on_complete,
                **options,
            )
        except Exception as e:
            self.state.is_processing = False
            self.state.status_text = _tr("common.failed", "Failed")
            self.state.error_message = str(e)
            self.page.run_thread(self._refresh_ui)
            self.page.run_thread(lambda: self._show_complete_dialog(0, len(run_paths), [str(e)]))

    def _show_complete_dialog(self, success: int, total: int, errors: List[str]):
        if not self.page:
            return
        if errors:
            dlg = ft.AlertDialog(
                title=ft.Text(_tr("common.error", "Error")),
                content=ft.Text(_tr("common.completed_with_errors", "Completed with errors.") + f"\n{len(errors)} items"),
                actions=[ft.TextButton("OK", on_click=lambda e: self.page.close(dlg))],
            )
        else:
            dlg = ft.AlertDialog(
                title=ft.Text(_tr("common.success", "Success")),
                content=ft.Text(f"{success}/{total} " + _tr("common.completed", "completed.") if total else _tr("common.completed", "completed.")),
                actions=[ft.TextButton("OK", on_click=lambda e: self.page.close(dlg))],
            )
        self.page.open(dlg)


def start_app(targets: List[str], mode: str = "convert"):
    app = MeshFletApp(targets, mode=mode)
    ft.run(app.main, view=ft.AppView.FLET_APP_HIDDEN)
