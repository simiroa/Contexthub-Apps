import flet as ft
from pathlib import Path
from typing import Optional
import os
import base64
from PIL import Image

from .service import TexturePackerService
from .state import PackerState
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import reveal_desktop_window
from utils.i18n import t


class TexturePackerFletApp:
    def __init__(self, target_path: Optional[str]):
        self.service = TexturePackerService()
        self.state = PackerState()
        self.target_path = Path(target_path) if target_path else None

        self.presets = {
            "ORM": ["Occlusion", "Roughness", "Metallic", ""],
            "ORM + Alpha": ["Occlusion", "Roughness", "Metallic", "Alpha"],
            "Unity Mask": ["Metallic", "Occlusion", "Detail", "Smoothness"],
            "Unreal ORM": ["Occlusion", "Roughness", "Metallic", ""],
            "Custom": ["Red", "Green", "Blue", "Alpha"],
        }
        self.slot_uis = {}
        self.file_picker = None
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"

    async def main(self, page: ft.Page):
        self.page = page
        title = t("texture_packer_gui.title") or "Texture Packer"
        configure_page(page, title, window_profile="wide_canvas")
        if not self.capture_mode:
            self.file_picker = ft.FilePicker()
            page.overlay.append(self.file_picker)
        page.update()

        self.setup_controls()
        self.setup_ui()
        self.apply_preset_logic("ORM")
        if self.target_path:
            self.on_auto_parse(None)
        await reveal_desktop_window(page)

    def setup_controls(self):
        self.slot_uis = {}
        for key in ["r", "g", "b", "a"]:
            color = {"r": COLORS["accent"], "g": "#6BCB77", "b": "#4D96FF", "a": "#9CA3AF"}[key]
            self.slot_uis[key] = {
                "txt_label": ft.TextField(
                    label=f"{key.upper()} Label",
                    height=40,
                    text_size=12,
                    border_color=color,
                    on_change=lambda e, k=key: self.on_label_change(e, k),
                ),
                "img_preview": ft.Image(src="", width=150, height=150, fit="contain", visible=False),
                "empty_text": ft.Text("여기에 놓기 또는 불러오기", size=12, color=COLORS["text_muted"], text_align="center"),
                "fn_text": ft.Text("", size=10, color=COLORS["text_muted"], no_wrap=True, width=150, text_align="center"),
            }

        self.dd_preset = ft.Dropdown(
            label="Preset",
            options=[ft.dropdown.Option(p) for p in self.presets.keys()],
            value="ORM",
            width=150,
            on_select=lambda e: self.apply_preset_logic(e.control.value),
        )
        self.txt_output = ft.TextField(label="Output Filename", value="_Packed", expand=True)
        self.dd_format = ft.Dropdown(
            label="Format",
            options=[ft.dropdown.Option(val) for val in [".png", ".jpg", ".tga", ".exr"]],
            value=".png",
            width=100,
        )
        self.chk_resize = ft.Checkbox(label="Resize", value=False, on_change=self.on_resize_toggle)
        self.dd_size = ft.Dropdown(
            options=[ft.dropdown.Option(s) for s in ["512", "1024", "2048", "4096"]],
            value="2048",
            width=100,
            disabled=True,
        )
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.status_text = ft.Text("준비", size=12, color=COLORS["text_muted"])
        self.btn_pack = ft.ElevatedButton(
            "Pack Textures",
            icon="compress",
            on_click=self.on_pack_click,
            bgcolor=COLORS["accent"],
            color=COLORS["text"],
            height=50,
            expand=True,
        )
        apply_button_sizing(self.btn_pack, "primary")

    def setup_ui(self):
        summary_bar = ft.Container(
            content=ft.Row([
                ft.Text("채널 슬롯에 텍스처를 배치하면 출력 이름과 프리셋이 함께 정리됩니다.", color=COLORS["text_muted"], expand=True),
                self.status_text,
            ], alignment="spaceBetween"),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
        )

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(t("texture_packer_gui.title") or "Texture Packer", size=22, weight="bold"),
                            ft.Text("여러 맵을 하나의 채널 패킹 텍스처로 정리합니다.", size=12, color=COLORS["text_muted"]),
                        ],
                        expand=True,
                    ),
                    self.dd_preset,
                    ft.IconButton(icon=ft.Icons.REFRESH, on_click=self.on_auto_parse, tooltip="Auto-Parse from Folder"),
                    ft.IconButton(icon=ft.Icons.DELETE_SWEEP, on_click=self.on_clear_all, tooltip="Clear All"),
                ],
                alignment="spaceBetween",
            ),
            padding=ft.padding.only(bottom=SPACING["md"]),
        )

        grid = ft.Row(
            [
                self.create_slot_column("r"),
                self.create_slot_column("g"),
                self.create_slot_column("b"),
                self.create_slot_column("a"),
            ],
            spacing=10,
            alignment="center",
        )

        output_section = ft.Container(
            content=ft.Column(
                [
                    ft.Row([self.txt_output, self.dd_format], spacing=10),
                    ft.Row([self.chk_resize, self.dd_size], spacing=10, wrap=True),
                    action_bar(status=self.status_text, primary=self.btn_pack, progress=self.progress_bar),
                ],
                spacing=10,
            ),
            padding=SPACING["md"],
            bgcolor=COLORS["surface_alt"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
        )

        self.page.add(
            ft.Container(
                content=ft.Column([header, summary_bar, grid, ft.Container(expand=True), output_section], expand=True),
                padding=SPACING["xl"],
                expand=True,
            )
        )

    def create_slot_column(self, key):
        ui = self.slot_uis[key]
        return ft.Column(
            [
                ui["txt_label"],
                ft.Container(
                    content=ft.Stack(
                        [
                            ft.Container(content=ui["empty_text"], alignment=ft.alignment.Alignment(0, 0)),
                            ft.Container(content=ui["img_preview"], alignment=ft.alignment.Alignment(0, 0)),
                        ]
                    ),
                    width=170,
                    height=170,
                    bgcolor=COLORS["surface"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["sm"],
                    on_click=lambda _, k=key: self.on_load_slot(k),
                    tooltip=f"Click to load {key.upper()} channel",
                ),
                ui["fn_text"],
                ft.Row(
                    [
                        ft.IconButton(icon=ft.Icons.FOLDER_OPEN, icon_size=16, on_click=lambda _, k=key: self.on_load_slot(k)),
                        ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16, on_click=lambda _, k=key: self.on_clear_slot(k)),
                    ],
                    alignment="center",
                ),
                ft.Text("불러오기 / 비우기", size=10, color=COLORS["text_muted"]),
            ],
            horizontal_alignment="center",
        )

    def on_load_slot(self, key):
        if self.file_picker is None:
            return
        files = self.file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
        if not files:
            return
        picked = Path(files[0].path)
        if picked.exists():
            self.load_path_to_slot(key, picked)

    def on_label_change(self, e, key):
        self.state.slots[key].label = e.control.value
        if self.state.current_preset != "Custom":
            self.state.current_preset = "Custom"
            self.dd_preset.value = "Custom"
            self.page.update()

    def apply_preset_logic(self, preset_name):
        self.state.current_preset = preset_name
        labels = self.presets.get(preset_name, self.presets["Custom"])
        for idx, key in enumerate(["r", "g", "b", "a"]):
            label = labels[idx]
            self.state.slots[key].label = label
            self.slot_uis[key]["txt_label"].value = label
        self.update_output_name_logic()
        self.page.update()

    def on_clear_slot(self, key):
        self.state.slots[key].path = None
        self.state.slots[key].preview_base64 = None
        ui = self.slot_uis[key]
        ui["img_preview"].visible = False
        ui["img_preview"].src = ""
        ui["empty_text"].visible = True
        ui["fn_text"].value = ""
        self.update_output_name_logic()
        self.page.update()

    def on_clear_all(self, _):
        for key in ["r", "g", "b", "a"]:
            self.on_clear_slot(key)

    def update_output_name_logic(self):
        loaded = [slot.path for slot in self.state.slots.values() if slot.path]
        if not loaded:
            return

        stems = [path.stem for path in loaded]
        left, right = min(stems), max(stems)
        common = left
        for idx, char in enumerate(left):
            if idx >= len(right) or char != right[idx]:
                common = left[:idx]
                break
        common = common.rstrip(" _-.") or "Packed"

        suffix = "_Packed"
        if self.state.current_preset == "ORM":
            suffix = "_ORM"
        elif self.state.current_preset == "Unity Mask":
            suffix = "_MaskMap"

        self.state.output_name = common + suffix
        self.txt_output.value = self.state.output_name
        self.page.update()

    def on_auto_parse(self, _):
        if not self.target_path:
            return
        labels = {key: slot.label for key, slot in self.state.slots.items()}
        found = self.service.auto_parse(self.target_path, labels)
        for key, path in found.items():
            self.load_path_to_slot(key, path)
        self.update_output_name_logic()

    def load_path_to_slot(self, key, path: Path):
        self.state.slots[key].path = path
        ui = self.slot_uis[key]
        ui["fn_text"].value = path.name
        try:
            with Image.open(path) as image:
                image.thumbnail((300, 300))
                raw = self.service.get_preview_bytes(image)
                encoded = raw if isinstance(raw, str) else base64.b64encode(raw).decode("ascii")
                ui["img_preview"].src = f"data:image/png;base64,{encoded}"
                ui["img_preview"].visible = True
                ui["empty_text"].visible = False
        except Exception:
            ui["img_preview"].visible = False
            ui["empty_text"].visible = True
        self.update_output_name_logic()
        self.page.update()

    def on_resize_toggle(self, e):
        self.state.resize_enabled = e.control.value
        self.dd_size.disabled = not e.control.value
        self.page.update()

    def on_pack_click(self, _):
        if self.state.is_processing:
            return

        input_slots = {key: slot.path for key, slot in self.state.slots.items() if slot.path}
        if not input_slots:
            self.status_text.value = "입력 텍스처가 없습니다."
            self.page.update()
            return

        self.state.is_processing = True
        self.btn_pack.disabled = True
        self.progress_bar.visible = True
        self.page.update()

        if self.target_path and self.target_path.parent.exists():
            out_dir = self.target_path.parent
        else:
            out_dir = Path.cwd()

        out_path = out_dir / f"{self.txt_output.value}{self.dd_format.value}"
        resize = None
        if self.chk_resize.value:
            value = int(self.dd_size.value)
            resize = (value, value)

        labels = {key: slot.label for key, slot in self.state.slots.items()}
        self.service.pack_textures(
            slots=input_slots,
            labels=labels,
            output_path=out_path,
            resize_size=resize,
            on_complete=self.handle_complete,
        )

    def handle_complete(self, success, result):
        self.state.is_processing = False
        self.btn_pack.disabled = False
        self.progress_bar.visible = False
        if success:
            self.status_text.value = f"{Path(result).name} 저장 완료"
        else:
            self.status_text.value = f"오류: {result}"
        self.page.update()


def start_app(target: Optional[str]):
    app = TexturePackerFletApp(target)
    ft.run(app.main, view=ft.AppView.FLET_APP_HIDDEN)
