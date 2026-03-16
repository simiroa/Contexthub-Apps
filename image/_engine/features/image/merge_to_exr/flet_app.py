import flet as ft
from pathlib import Path
from typing import List, Optional
import os

from .service import ExrMergeService
from .state import ExrMergeState, ChannelConfig
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import reveal_desktop_window
from utils.i18n import t

class ChannelRow(ft.Container):
    def __init__(self, config: ChannelConfig, file_options: List[str], on_delete: callable, on_change: callable):
        super().__init__()
        self.config = config
        self.on_delete_cb = on_delete
        self.on_change_cb = on_change
        
        self.padding = ft.padding.symmetric(vertical=SPACING["xs"], horizontal=SPACING["sm"])
        self.bgcolor = COLORS["surface"]
        self.border_radius = RADII["sm"]
        
        self.chk_enabled = ft.Checkbox(value=config.enabled, on_change=self._handle_change)
        self.dd_file = ft.Dropdown(
            options=[ft.dropdown.Option(f) for f in file_options],
            value=config.source_file,
            on_select=self._handle_change,
            expand=2,
            height=35,
            text_size=12,
        )
        self.tf_name = ft.TextField(
            value=config.target_name,
            on_change=self._handle_change,
            expand=2,
            height=35,
            text_size=12,
            content_padding=5,
        )
        self.dd_mode = ft.Dropdown(
            options=[ft.dropdown.Option(m) for m in ["RGB", "RGBA", "R", "G", "B", "A", "L"]],
            value=config.mode,
            on_select=self._handle_change,
            width=80,
            height=35,
            text_size=11,
        )
        self.chk_inv = ft.Checkbox(label="Inv", value=config.invert, on_change=self._handle_change, scale=0.8)
        self.chk_lin = ft.Checkbox(label="Lin", value=config.linear, on_change=self._handle_change, scale=0.8)
        
        self.content = ft.Row([
            self.chk_enabled,
            self.dd_file,
            ft.Icon(ft.Icons.ARROW_FORWARD, size=12, color=COLORS["line"]),
            self.tf_name,
            self.dd_mode,
            ft.Row([self.chk_inv, self.chk_lin], spacing=0),
            ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16, icon_color=COLORS["danger"], on_click=lambda _: self.on_delete_cb(self))
        ], spacing=SPACING["sm"], vertical_alignment="center")

    def _handle_change(self, _):
        self.config.enabled = self.chk_enabled.value
        self.config.source_file = self.dd_file.value
        self.config.target_name = self.tf_name.value
        self.config.mode = self.dd_mode.value
        self.config.invert = self.chk_inv.value
        self.config.linear = self.chk_lin.value
        self.on_change_cb()

class ExrMergeFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = ExrMergeService()
        self.state = ExrMergeState(files=[Path(f) for f in initial_files])
        self.file_names = [f.name for f in self.state.files]
        self.rows_container = ft.Column(scroll="auto", expand=True)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.status_text = ft.Text("준비", size=12, color=COLORS["text_muted"])
        self.btn_export = ft.ElevatedButton(
            t("merge_exr.export_btn"),
            icon="save",
            on_click=self.on_export_click,
            bgcolor=COLORS["accent"],
            color=COLORS["text"],
            height=45,
        )
        apply_button_sizing(self.btn_export, "primary")

    async def main(self, page: ft.Page):
        self.page = page
        title = t("merge_exr.header") or "EXR Merger"
        configure_page(page, title, window_profile="table_heavy")
        page.update()
        
        self.setup_ui()
        self.auto_create_channels()
        await reveal_desktop_window(page)

    def setup_ui(self):
        header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text(t("merge_exr.header") or "EXR Merger", size=24, weight="bold"),
                        ft.Text("소스 이미지를 EXR 레이어에 매핑한 뒤 멀티레이어 파일 하나로 내보냅니다.", size=12, color=COLORS["text_muted"]),
                    ], expand=True),
                    apply_button_sizing(ft.ElevatedButton(t("merge_exr.add_custom") or "Add Layer", icon=ft.Icons.ADD, on_click=self.on_add_layer), "toolbar"),
                    ft.IconButton(icon=ft.Icons.DELETE_SWEEP, on_click=self.on_clear_all, tooltip="Clear All")
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

        table_header = ft.Container(
            content=ft.Row([
                ft.Text("사용", width=56, weight="bold", size=12),
                ft.Text("소스 파일", expand=2, weight="bold", size=12),
                ft.Text("레이어 이름", expand=2, weight="bold", size=12),
                ft.Text("채널", width=90, weight="bold", size=12),
                ft.Text("옵션", width=110, weight="bold", size=12),
                ft.Container(width=34),
            ], spacing=SPACING["sm"]),
            padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
        )

        footer = ft.Container(
            content=action_bar(
                status=ft.Text("저장 위치: 입력 파일 폴더", color=COLORS["text_muted"], size=12),
                primary=self.btn_export,
                progress=self.progress_bar,
            ),
            padding=ft.padding.only(top=SPACING["md"])
        )

        self.page.add(
            ft.Container(
                content=ft.Column([
                    header,
                    ft.Container(
                        content=ft.Column([
                            table_header,
                            ft.Divider(height=1, color=COLORS["line"]),
                            self.rows_container,
                        ], expand=True),
                        expand=True,
                        padding=SPACING["sm"],
                        bgcolor=COLORS["surface_alt"],
                        border_radius=RADII["md"],
                        border=ft.border.all(1, COLORS["line"]),
                    ),
                    footer
                ], expand=True),
                padding=SPACING["xl"],
                expand=True
            )
        )

    def auto_create_channels(self):
        self.state.channels.clear()
        self.rows_container.controls.clear()
        
        if not self.state.files:
            self.status_text.value = "입력 파일을 추가해 주세요"
            self.rows_container.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.LAYERS_OUTLINED, size=28, color=COLORS["text_muted"]),
                        ft.Text("이미지를 추가하면 여기에서 레이어 구성을 시작할 수 있습니다.", color=COLORS["text_muted"]),
                    ], horizontal_alignment="center", alignment="center"),
                    padding=SPACING["xl"],
                    alignment=ft.alignment.Alignment(0, 0),
                )
            )
            self.page.update()
            return
        
        all_stems = [f.stem for f in self.state.files]
        common = os.path.commonprefix(all_stems)
        if len(common) < 3 or len(common) == len(all_stems[0]): common = ""
        self.state.common_prefix = common

        for f in self.state.files:
            f_lower = f.name.lower()
            mode = "RGB"
            if any(x in f_lower for x in ["_ao", "ambient", "occlusion", "roughness", "_rough", "metallic", "_mask", "_alpha", "opacity", "_gray"]):
                mode = "L"
            
            target_name = f.stem
            if common and target_name.startswith(common):
                target_name = target_name[len(common):].lstrip("_-. ")
            if not target_name: target_name = f.stem
            
            cfg = ChannelConfig(source_file=f.name, target_name=target_name, mode=mode)
            self.state.channels.append(cfg)
            self.rows_container.controls.append(ChannelRow(cfg, self.file_names, self.delete_row, self.update_status))
            
        self.update_status()

    def on_add_layer(self, _):
        cfg = ChannelConfig(target_name=f"Layer_{len(self.state.channels)+1}")
        self.state.channels.append(cfg)
        self.rows_container.controls.append(ChannelRow(cfg, self.file_names, self.delete_row, self.update_status))
        self.page.update()

    def on_clear_all(self, _):
        self.state.channels.clear()
        self.rows_container.controls.clear()
        self.status_text.value = "준비"
        self.page.update()

    def delete_row(self, row_ctrl: ChannelRow):
        self.state.channels.remove(row_ctrl.config)
        self.rows_container.controls.remove(row_ctrl)
        self.page.update()

    def update_status(self):
        enabled_count = sum(1 for c in self.state.channels if c.enabled)
        self.status_text.value = f"활성 레이어 {enabled_count}개"
        self.page.update()

    def on_export_click(self, _):
        if self.state.is_exporting: return
        missing = self.service.get_missing_dependencies()
        if missing:
            self.status_text.value = "Missing deps: " + ", ".join(missing)
            self.page.update()
            return
        
        self.state.is_exporting = True
        self.btn_export.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.page.update()

        base_dir = self.state.files[0].parent if self.state.files else Path(".")
        
        self.service.export_exr(
            base_dir=base_dir,
            channels=self.state.channels,
            all_files=self.state.files,
            on_progress=self.handle_progress,
            on_complete=self.handle_complete
        )

    def handle_progress(self, progress, status):
        self.progress_bar.value = progress
        self.status_text.value = status
        self.page.update()

    def handle_complete(self, success, result):
        self.state.is_exporting = False
        self.btn_export.disabled = False
        self.progress_bar.visible = False
        
        if success:
            self.status_text.value = "Done: MultiLayer_Output.exr"
            def close_dlg(e):
                self.page.dialog.open = False
                self.page.update()
                self.page.window_close()
                
            self.page.dialog = ft.AlertDialog(
                title=ft.Text("Export Successful"),
                content=ft.Text(f"Saved to:\n{result}"),
                actions=[ft.TextButton("Open Folder", on_click=lambda _: os.startfile(Path(result).parent)), ft.TextButton("OK", on_click=close_dlg)],
            )
        else:
            self.status_text.value = "Error"
            self.page.dialog = ft.AlertDialog(
                title=ft.Text("Export Failed"),
                content=ft.Text(result),
                actions=[ft.TextButton("OK", on_click=lambda e: setattr(self.page.dialog, 'open', False))],
            )
            
        self.page.dialog.open = True
        self.page.update()

def start_app(initial_files: List[str]):
    app = ExrMergeFletApp(initial_files)
    ft.run(app.main, view=ft.AppView.FLET_APP_HIDDEN)
