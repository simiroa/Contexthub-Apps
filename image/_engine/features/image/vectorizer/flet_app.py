import flet as ft
from pathlib import Path
from typing import List, Optional
import os

from .service import VectorizerService
from .state import VectorizerState, LayerStateEntry
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import apply_desktop_window
from utils.i18n import t

class VectorizerFletApp:
    def __init__(self, initial_paths: List[str]):
        self.service = VectorizerService()
        self.state = VectorizerState()
        self.initial_paths = [Path(p) for p in initial_paths if Path(p).exists()]
        
    def main(self, page: ft.Page):
        self.page = page
        title = t("rigready_vectorizer_gui.title") or "RigReady Vectorizer"
        configure_page(page, title, window_profile="two_pane")
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        if not self.capture_mode:
            self.file_picker = ft.FilePicker()
            page.overlay.append(self.file_picker)
        page.update()
        
        self.setup_controls()
        self.setup_ui()
        
        if self.initial_paths:
            self.load_files(self.initial_paths)

    def setup_controls(self):
        # Layer List
        self.layer_list = ft.Column(scroll="auto", expand=True, spacing=5)
        self.lbl_layer_count = ft.Text("(0/0)", size=12, color=COLORS["text_muted"])
        
        # Settings
        self.sl_speckle = ft.Slider(min=1, max=20, value=4, divisions=19, label="{value}", on_change=self.on_param_change)
        self.sl_color = ft.Slider(min=1, max=10, value=6, divisions=9, label="{value}", on_change=self.on_param_change)
        self.sl_corner = ft.Slider(min=15, max=180, value=60, divisions=33, label="{value}", on_change=self.on_param_change)
        
        self.chk_remove_bg = ft.Checkbox(label="Remove Background (rembg)", value=True, on_change=self.on_param_change)
        self.chk_gen_jsx = ft.Checkbox(label="Generate AE JSX Script", value=True, on_change=self.on_param_change)
        self.chk_split_paths = ft.Checkbox(label="Split paths to layers", value=False, on_change=self.on_param_change)
        self.chk_use_anchor = ft.Checkbox(label="Use Anchor Estimation", value=True, on_change=self.on_param_change)
        self.chk_skip_text = ft.Checkbox(label="Skip Text Layers", value=False, on_change=self.on_param_change)
        self.chk_skip_smart = ft.Checkbox(label="Skip Smart Objects", value=False, on_change=self.on_param_change)
        
        self.tf_output = ft.TextField(label="Output Folder", expand=True, read_only=True, text_size=12)
        self.btn_browse = ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=self.browse_output)
        
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])
        
        self.btn_run = ft.ElevatedButton(
            "Run Vectorizer",
            icon="play_arrow",
            on_click=self.on_run_click,
            bgcolor=COLORS["accent"],
            color=COLORS["text"],
            height=50,
            expand=True
        )

    def setup_ui(self):
        summary_bar = ft.Container(
            content=ft.Row([
                ft.Text("레이어 선택 후 벡터화 옵션을 조정하고 실행합니다.", color=COLORS["text_muted"], expand=True),
                self.lbl_layer_count,
            ], alignment="spaceBetween"),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
        )

        # Left Pane: Layers
        left_pane = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text(t("rigready_vectorizer_gui.title") or "RigReady Vectorizer", size=22, weight="bold", no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text("Vectorize image layers for rigging", size=12, color=COLORS["text_muted"]),
                    ], expand=True),
                    ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=self.on_pick_file, tooltip="Load Image/EXR"),
                    ft.IconButton(ft.Icons.DELETE_SWEEP, on_click=self.on_clear_all, tooltip="Clear All")
                ], alignment="spaceBetween"),
                ft.Row([
                    ft.TextButton("All", on_click=lambda _: self.toggle_all(True)),
                    ft.TextButton("None", on_click=lambda _: self.toggle_all(False)),
                    ft.Container(expand=True),
                    self.lbl_layer_count
                ], alignment="spaceBetween"),
                ft.Container(
                    content=self.layer_list,
                    expand=True,
                    padding=5,
                    bgcolor=COLORS["surface"],
                    border_radius=RADII["md"],
                    border=ft.border.all(1, COLORS["line"])
                )
            ], expand=True),
            expand=True
        )

        # Right Pane: Settings
        right_pane = ft.Container(
            content=ft.Column([
                ft.Text("Settings", size=16, weight="bold"),
                ft.Text("기본 품질 설정", size=12, color=COLORS["text_muted"]),
                ft.Column([
                    ft.Text("Filter Speckle (Noise Reduction)", size=12),
                    self.sl_speckle,
                    ft.Text("Color Precision", size=12),
                    self.sl_color,
                    ft.Text("Corner Threshold", size=12),
                    self.sl_corner,
                ], spacing=2),
                ft.Divider(color=COLORS["line"]),
                ft.Column([
                    self.chk_remove_bg,
                    self.chk_gen_jsx,
                    self.chk_split_paths,
                    self.chk_use_anchor,
                    self.chk_skip_text,
                    self.chk_skip_smart,
                ], spacing=0),
                ft.Container(
                    content=ft.Column([
                        ft.Text("출력 폴더", size=12, color=COLORS["text_muted"]),
                        ft.Row([self.tf_output, self.btn_browse], vertical_alignment="end"),
                    ], spacing=6),
                ),
                ft.Container(expand=True),
                self.progress_bar,
                ft.Row([self.status_text], alignment="start"),
                self.btn_run,
            ], spacing=SPACING["md"], expand=True),
            expand=True,
            padding=SPACING["lg"],
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"])
        )

        self.page.add(
            ft.Container(
                content=ft.Column([
                    summary_bar,
                    ft.Row([left_pane, right_pane], spacing=SPACING["lg"], expand=True),
                ], spacing=SPACING["md"], expand=True),
                padding=SPACING["xl"],
                expand=True
            )
        )

    def load_files(self, paths: List[Path]):
        self.status_text.value = "Analyzing files..."
        self.page.update()
        
        layers = self.service.load_files(paths)
        self.state.layers = layers
        if layers and not self.state.output_dir:
            self.state.output_dir = str(paths[0].parent / "vectorized")
            self.tf_output.value = self.state.output_dir
            
        self.refresh_layer_list()
        self.status_text.value = "Ready"
        self.page.update()

    def refresh_layer_list(self):
        self.state.update_layer_visibility()
        self.layer_list.controls.clear()
        
        visible_layers = [l for l in self.state.layers if l.visible]
        selected_count = sum(1 for l in self.state.layers if l.selected and l.visible)
        self.lbl_layer_count.value = f"({selected_count}/{len(visible_layers)})"

        for layer in visible_layers:
            badge = ""
            if layer.is_text: badge = "[T] "
            elif layer.is_smart_object: badge = "[S] "
            
            self.layer_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Checkbox(value=layer.selected, on_change=lambda e, l=layer: self.on_layer_toggle(e, l)),
                        ft.Column([
                            ft.Text(f"{badge}{layer.display_name}", size=13, weight="bold", overflow="ellipsis"),
                            ft.Text(f"{layer.width}x{layer.height}", size=10, color=COLORS["text_muted"]),
                        ], spacing=0, expand=True),
                    ], spacing=2),
                    padding=ft.padding.symmetric(vertical=2),
                    border=ft.border.only(bottom=ft.BorderSide(1, COLORS["line"]))
                )
            )
        self.page.update()

    def on_layer_toggle(self, e, layer):
        layer.selected = e.control.value
        self.refresh_layer_list()

    def toggle_all(self, val):
        for l in self.state.layers:
            if l.visible: l.selected = val
        self.refresh_layer_list()

    def on_param_change(self, _):
        self.state.speckle = int(self.sl_speckle.value)
        self.state.color_precision = int(self.sl_color.value)
        self.state.corner_threshold = int(self.sl_corner.value)
        self.state.remove_bg = self.chk_remove_bg.value
        self.state.gen_jsx = self.chk_gen_jsx.value
        self.state.split_paths = self.chk_split_paths.value
        self.state.use_anchor = self.chk_use_anchor.value
        self.state.skip_text = self.chk_skip_text.value
        self.state.skip_smart = self.chk_skip_smart.value
        self.refresh_layer_list()

    def browse_output(self, _):
        if not hasattr(self, "file_picker"):
            return
        selected_dir = self.file_picker.get_directory_path(
            initial_directory=self.state.output_dir or None
        )
        if selected_dir:
            self.state.output_dir = selected_dir
            self.tf_output.value = selected_dir
            self.page.update()

    def on_pick_file(self, _):
        if not hasattr(self, "file_picker"):
            return
        files = self.file_picker.pick_files(
            allow_multiple=True,
            allowed_extensions=[
                "png", "jpg", "jpeg", "bmp", "tga", "tif", "tiff", "webp", "exr", "psd", "psb"
            ],
        )
        if not files:
            return
        picked = []
        for file in files:
            path = Path(file.path)
            if path.exists():
                picked.append(path)
        if picked:
            self.load_files(picked)

    def on_clear_all(self, _):
        self.state.layers.clear()
        self.state.source_files.clear()
        self.layer_list.controls.clear()
        self.lbl_layer_count.value = "(0/0)"
        self.status_text.value = "Ready"
        self.btn_run.disabled = False
        self.page.update()

    def on_run_click(self, _):
        if self.state.is_processing: return
        missing = self.service.get_missing_dependencies()
        hard_missing = [dep for dep in missing if dep == "vtracer"]
        if hard_missing:
            self.status_text.value = "Missing deps: " + ", ".join(hard_missing)
            self.page.update()
            return
        
        selected = [l for l in self.state.layers if l.selected and l.visible]
        if not selected:
            self.status_text.value = "Error: No layers selected"
            self.page.update()
            return
        
        if not self.state.output_dir:
            fallback = Path.cwd() / "vectorized"
            self.state.output_dir = str(fallback)
            self.tf_output.value = self.state.output_dir

        self.state.is_processing = True
        self.btn_run.disabled = True
        self.progress_bar.visible = True
        self.page.update()

        config = {
            "filter_speckle": self.state.speckle,
            "color_precision": self.state.color_precision,
            "corner_threshold": self.state.corner_threshold
        }
        options = {
            "remove_bg": self.state.remove_bg,
            "gen_jsx": self.state.gen_jsx,
            "split_paths": self.state.split_paths,
            "use_anchor": self.state.use_anchor
        }

        self.service.run_vectorization(
            selected_layers=selected,
            output_dir=Path(self.state.output_dir),
            config=config,
            options=options,
            on_progress=self.handle_progress,
            on_complete=self.handle_complete
        )

    def handle_progress(self, progress, status):
        self.progress_bar.value = progress
        self.status_text.value = status
        self.page.update()

    def handle_complete(self, success, message):
        self.state.is_processing = False
        self.btn_run.disabled = False
        self.progress_bar.visible = False
        self.status_text.value = message
        self.page.update()

def start_app(targets: List[str]):
    app = VectorizerFletApp(targets)
    ft.app(target=app.main)
