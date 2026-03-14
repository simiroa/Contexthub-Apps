import flet as ft
from pathlib import Path
from typing import List, Optional, Dict
import os

from .service import SplitExrService
from .state import SplitExrState, LayerConfig
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import apply_desktop_window
from utils.i18n import t

class SplitExrFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = SplitExrService()
        self.state = SplitExrState(files=[Path(f) for f in initial_files if Path(f).exists()])
        
        self.presets = {
            "Standard": ["_Red", "_Green", "_Blue", "_Alpha"],
            "Unity MaskMap": ["_Metallic", "_Occlusion", "_Detail", "_Smoothness"],
            "Unreal ORM": ["_Occlusion", "_Roughness", "_Metallic", "_Specular"],
            "Texture Packing": ["_R", "_G", "_B", "_A"]
        }

    def main(self, page: ft.Page):
        self.page = page
        title = t("image_split_exr.title") or "Image Channel Splitter"
        configure_page(page, title, window_profile="table_heavy")
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        if not self.capture_mode:
            self.file_picker = ft.FilePicker()
            page.overlay.append(self.file_picker)
        page.update()
        
        self.setup_controls()
        self.setup_ui()
        self.update_file_list_ui()
        
        if self.state.files:
            self.analyze_primary_file()

    def setup_controls(self):
        # File list
        self.file_list_column = ft.Column(spacing=2, scroll="auto")
        
        # Layer Table Header
        self.layer_header = ft.Row([
            ft.Text("Channel / Layer", size=12, weight="bold", expand=True),
            ft.Text("Inv", size=12, weight="bold", width=30, text_align="center"),
            ft.Text("Suffix", size=12, weight="bold", width=150),
        ], spacing=10)
        
        self.layers_column = ft.Column(spacing=2, scroll="auto")
        self.layers_column.controls.append(
            ft.Text("파일을 추가하면 감지된 채널이 여기에 표시됩니다.", color=COLORS["text_muted"])
        )
        
        # Format & Preset
        self.dd_format = ft.Dropdown(
            label="Format",
            options=[ft.dropdown.Option(f) for f in ["PNG", "JPG", "TGA", "EXR"]],
            value="PNG",
            width=100,
        )
        
        self.dd_preset = ft.Dropdown(
            label="Naming Preset",
            options=[ft.dropdown.Option(p) for p in self.presets.keys()],
            width=180,
            on_select=self.apply_preset
        )

        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.status_text = ft.Text("준비", size=12, color=COLORS["text_muted"])
        self.btn_extract = ft.ElevatedButton(
            "Extract Channels",
            icon="content_cut",
            on_click=self.on_extract_click,
            height=50,
            expand=True,
            disabled=not bool(self.state.files),
        )
        apply_button_sizing(self.btn_extract, "primary")

    def setup_ui(self):
        header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text(t("image_split_exr.title") or "Image Channel Splitter", size=22, weight="bold"),
                        ft.Text("원본 이미지를 선택하고 감지된 채널을 검토한 뒤 한 번에 추출합니다.", size=12, color=COLORS["text_muted"]),
                    ], expand=True),
                    ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=self.on_pick_files, tooltip="Add Files"),
                    ft.IconButton(ft.Icons.DELETE_SWEEP, on_click=self.on_clear_all, tooltip="Clear All")
                ], alignment="spaceBetween"),
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"입력 파일 {len(self.state.files)}개", color=COLORS["text_muted"]),
                        ft.VerticalDivider(width=16, color="transparent"),
                        self.status_text,
                    ], wrap=True),
                    padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
                    bgcolor=COLORS["surface"],
                    border_radius=RADII["md"],
                ),
            ]),
            padding=ft.padding.only(bottom=SPACING["md"])
        )

        # File List Box
        files_box = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("입력 파일", size=12, weight="bold", expand=True),
                    apply_button_sizing(ft.TextButton("추가", icon=ft.Icons.ADD, on_click=self.on_pick_files), "compact"),
                    ft.TextButton("비우기", icon=ft.Icons.DELETE_OUTLINE, on_click=self.on_clear_all),
                ]),
                ft.Container(
                    content=self.file_list_column,
                    height=100,
                    bgcolor=COLORS["surface"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    padding=5
                )
            ], spacing=5)
        )

        # Config Area
        config_box = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Channels Configuration", size=14, weight="bold", expand=True),
                    self.dd_preset,
                    self.dd_format,
                ], spacing=10, vertical_alignment="center"),
                ft.Container(
                    content=ft.Column([
                        self.layer_header,
                        ft.Divider(height=1, color=COLORS["line"]),
                        self.layers_column
                    ], expand=True),
                    expand=True,
                    bgcolor=COLORS["surface"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["md"],
                    padding=10
                )
            ], spacing=10, expand=True),
            expand=True
        )

        # Layout
        self.page.add(
            ft.Container(
                content=ft.Column([
                    header,
                    files_box,
                    ft.Container(height=10),
                    config_box,
                    action_bar(
                        status=ft.Text("결과는 원본 기준 `_split` 폴더에 저장됩니다.", size=12, color=COLORS["text_muted"]),
                        primary=self.btn_extract,
                        progress=self.progress_bar,
                    ),
                ], expand=True),
                padding=SPACING["xl"],
                expand=True
            )
        )

    def update_file_list_ui(self):
        self.file_list_column.controls.clear()
        if not self.state.files:
            self.file_list_column.controls.append(
                ft.Text("채널을 분리할 이미지를 추가해 주세요.", size=11, color=COLORS["text_muted"])
            )
            self.btn_extract.disabled = True
            self.page.update()
            return
        for i, path in enumerate(self.state.files):
            self.file_list_column.controls.append(
                ft.Row([
                    ft.Text(f"{i+1}.", size=11, width=25),
                    ft.Text(path.name, size=11, expand=True, no_wrap=True),
                ], spacing=5)
            )
        self.btn_extract.disabled = not bool(self.state.files) or self.state.is_processing
        self.page.update()

    def on_pick_files(self, _):
        if self.file_picker is not None:
            files = self.file_picker.pick_files(
                allow_multiple=True,
                allowed_extensions=["exr", "png", "jpg", "jpeg", "tga", "tif", "tiff", "bmp"],
            )
            self._consume_files(files)

    def on_file_result(self, e):
        self._consume_files(getattr(e, "files", None))

    def _consume_files(self, files):
        if not files:
            return
        known = {str(path.resolve()) for path in self.state.files}
        added = False
        for file in files:
            path = Path(file.path)
            if not path.exists():
                continue
            resolved = str(path.resolve())
            if resolved in known:
                continue
            self.state.files.append(path)
            known.add(resolved)
            added = True
        if added:
            self.analyze_primary_file()

    def on_clear_all(self, _):
        self.state.files.clear()
        self.state.layers.clear()
        self.layers_column.controls.clear()
        self.layers_column.controls.append(
            ft.Text("파일을 추가하면 감지된 채널이 여기에 표시됩니다.", color=COLORS["text_muted"])
        )
        self.file_list_column.controls.clear()
        self.btn_extract.disabled = True
        self.status_text.value = "준비"
        self.page.update()

    def analyze_primary_file(self):
        if not self.state.files: return
        self.update_file_list_ui()
        
        info, layers_info = self.service.analyze_file(self.state.files[0])
        self.state.primary_info = info
        self.status_text.value = info
        
        # Populate layers
        self.state.layers.clear()
        self.layers_column.controls.clear()
        
        common_suffixes = ["_Red", "_Green", "_Blue", "_Alpha", "_Gray", "_R", "_G", "_B", "_A", "_Mask", "_Roughness", "_Metallic", "_Normal", "_Height", "_AO"]
        
        for idx, l in enumerate(layers_info):
            cfg = LayerConfig(
                name=l["name"],
                suffix=l["default_suffix"],
                channels=l["channels"]
            )
            self.state.layers.append(cfg)
            
            # Row UI
            suffix_opts = list(common_suffixes)
            if cfg.suffix not in suffix_opts: suffix_opts.insert(0, cfg.suffix)
            
            chk_layer = ft.Checkbox(label=l["name"], value=True, data=idx, on_change=self.on_layer_toggle, expand=True)
            chk_inv = ft.Checkbox(value=False, data=idx, on_change=self.on_invert_toggle)
            dd_suffix = ft.Dropdown(
                value=cfg.suffix,
                options=[ft.dropdown.Option(s) for s in suffix_opts],
                width=150,
                dense=True,
                data=idx,
                on_select=self.on_suffix_change
            )
            
            row = ft.Container(
                content=ft.Row([
                    chk_layer,
                    ft.Container(content=chk_inv, width=30, alignment=ft.alignment.Alignment(0, 0)),
                    dd_suffix
                ], spacing=10),
                bgcolor=COLORS["surface"] if idx % 2 == 0 else "transparent",
                padding=5,
                border_radius=RADII["sm"]
            )
            self.layers_column.controls.append(row)
            
        if self.state.files[0].suffix.lower() == ".exr":
            self.dd_format.value = "EXR"
        
        self.btn_extract.disabled = (len(self.state.layers) == 0)
        self.page.update()

    def on_layer_toggle(self, e):
        self.state.layers[e.control.data].enabled = e.control.value

    def on_invert_toggle(self, e):
        self.state.layers[e.control.data].invert = e.control.value

    def on_suffix_change(self, e):
        self.state.layers[e.control.data].suffix = e.control.value

    def apply_preset(self, e):
        preset_name = e.control.value
        suffixes = self.presets.get(preset_name, [])
        for i, cfg in enumerate(self.state.layers):
            if i < len(suffixes):
                cfg.suffix = suffixes[i]
                self.layers_column.controls[i].content.controls[2].value = suffixes[i]
        self.page.update()

    def on_extract_click(self, _):
        if self.state.is_processing: return
        
        selected_layers = [
            {"name": l.name, "invert": l.invert, "suffix": l.suffix, "channels": l.channels}
            for l in self.state.layers if l.enabled
        ]
        
        if not selected_layers: return
        
        self.state.is_processing = True
        self.btn_extract.disabled = True
        self.progress_bar.visible = True
        self.page.update()
        
        self.service.run_batch_split(
            files=self.state.files,
            layer_configs=selected_layers,
            format_ext=self.dd_format.value,
            on_progress=self.handle_progress,
            on_complete=self.handle_complete
        )

    def handle_progress(self, progress, status):
        self.progress_bar.value = progress
        self.status_text.value = status
        self.page.update()

    def handle_complete(self, success_count, errors):
        self.state.is_processing = False
        self.btn_extract.disabled = False
        self.progress_bar.visible = False
        
        if not errors:
            self.status_text.value = f"Successfully split {success_count} files."
        else:
            self.status_text.value = f"Completed with {len(errors)} errors."
            
        self.page.update()

def start_app(targets: List[str]):
    app = SplitExrFletApp(targets)
    ft.app(target=app.main)
