import flet as ft
from pathlib import Path
from typing import List, Optional
import os

from .service import ImageConvertService
from .state import ImageConvertState
from contexthub.ui.flet.tokens import COLORS, SPACING, RADII
from contexthub.ui.flet.layout import action_bar, apply_button_sizing, toolbar_row
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.window import apply_desktop_window
from utils.i18n import t

class ImageConvertFletApp:
    def __init__(self, initial_files: List[str]):
        self.service = ImageConvertService()
        self.state = ImageConvertState(files=[Path(f) for f in initial_files])
        
        # UI Controls
        self.files_summary = ft.Column(scroll="auto", expand=True)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=COLORS["accent"])
        self.status_text = ft.Text(t("common.ready"), size=12, color=COLORS["text_muted"])
        self.lbl_file_count = ft.Text(f"{len(self.state.files)} files", size=12, color=COLORS["text_muted"])
        self.btn_convert = ft.ElevatedButton(
            t("image_convert_gui.convert_button") or "Convert Images",
            icon="play_arrow",
            on_click=self.on_convert_click,
            bgcolor=COLORS["accent"],
            color=COLORS["text"],
            height=45,
        )
        apply_button_sizing(self.btn_convert, "primary")
        self.file_picker: Optional[ft.FilePicker] = None
        self.resize_combo: Optional[ft.Dropdown] = None
        self.capture_mode = os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"
        self.summary_text = ft.Text("", size=12, color=COLORS["text_muted"])
        self.destination_text = ft.Text("", size=12, color=COLORS["text_muted"])
        self.delete_checkbox: Optional[ft.Checkbox] = None

    def main(self, page: ft.Page):
        self.page = page
        title = t("image_convert_gui.header")
        configure_page(page, title, window_profile="form")
        if not self.capture_mode:
            self.file_picker = ft.FilePicker()
            page.overlay.append(self.file_picker)
        page.update()
        
        self.setup_ui()
        self.update_file_list()

    def setup_ui(self):
        header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text(t("image_convert_gui.header"), size=24, weight="bold"),
                        ft.Text("이미지를 불러오고 출력 형식을 선택한 뒤 한 번에 변환합니다.", size=12, color=COLORS["text_muted"]),
                    ], expand=True),
                    apply_button_sizing(ft.ElevatedButton("파일 추가", icon=ft.Icons.ADD_PHOTO_ALTERNATE, on_click=self.on_pick_files), "toolbar"),
                    ft.IconButton(ft.Icons.DELETE_SWEEP, on_click=self.on_clear_files, tooltip="Clear List"),
                ], alignment="spaceBetween"),
                ft.Container(
                    content=ft.Row([
                        self.lbl_file_count,
                        ft.VerticalDivider(width=16, color="transparent"),
                        self.summary_text,
                        ft.VerticalDivider(width=16, color="transparent"),
                        self.destination_text,
                    ], wrap=True),
                    padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
                    bgcolor=COLORS["surface"],
                    border_radius=RADII["md"],
                ),
            ]),
            padding=ft.padding.only(bottom=SPACING["md"])
        )

        file_list_container = ft.Container(
            content=ft.Column([
                ft.Text("입력 > 출력 미리보기", weight="bold"),
                ft.Container(
                    content=self.files_summary,
                    height=180,
                    padding=SPACING["sm"],
                    bgcolor=COLORS["surface"],
                    border_radius=RADII["md"],
                    border=ft.border.all(1, COLORS["line"]),
                ),
            ], spacing=SPACING["sm"]),
        )

        self.resize_combo = ft.Dropdown(
            options=[ft.dropdown.Option(s) for s in ["256", "512", "1024", "2048", "4096"]],
            value="1024",
            on_select=lambda e: setattr(self.state, "resize_size", e.control.value),
            width=120,
            disabled=True,
        )
        format_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(f) for f in ["PNG", "JPG", "WEBP", "BMP", "TGA", "TIFF", "ICO", "DDS", "EXR"]],
            value="PNG",
            on_select=self.on_format_change,
            width=170,
        )

        self.delete_checkbox = ft.Checkbox(
            label=t("image_convert_gui.delete_original"),
            on_change=lambda e: setattr(self.state, "delete_original", e.control.value),
            label_style=ft.TextStyle(color=COLORS["danger"]),
        )
        options_card = ft.Container(
            content=ft.Column([
                ft.Text("변환 설정", size=16, weight="bold"),
                ft.Row([
                    ft.Column([
                        ft.Text(t("image_convert_gui.format_label"), weight="bold"),
                        format_dropdown,
                    ], spacing=6, expand=True),
                    ft.Column([
                        ft.Text("크기 조정", weight="bold"),
                        ft.Row([
                            ft.Checkbox(label="크기 조정", on_change=self.on_resize_toggle),
                            self.resize_combo,
                        ]),
                    ], spacing=6, expand=True),
                ], spacing=SPACING["lg"]),
                ft.Row([
                    ft.Checkbox(label=t("image_convert_gui.save_to_folder"), on_change=self.on_save_folder_toggle),
                    self.delete_checkbox,
                ], spacing=SPACING["lg"], wrap=True),
            ], spacing=SPACING["md"]),
            padding=SPACING["md"],
            bgcolor=COLORS["surface_alt"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
        )

        action_bar_container = action_bar(
            status=self.status_text,
            primary=self.btn_convert,
            progress=self.progress_bar,
            secondary=[ft.TextButton(t("common.cancel"), on_click=lambda _: self.page.window_close())],
        )

        self.page.add(
            ft.Container(
                content=ft.Column([
                    header,
                    file_list_container,
                    options_card,
                    action_bar_container,
                ], expand=True),
                padding=SPACING["xl"],
                expand=True
            )
        )

    def update_file_list(self):
        self.files_summary.controls.clear()
        target_ext = self.state.target_format.lower()
        if target_ext == "png": target_ext = ".png"
        elif target_ext == "jpg": target_ext = ".jpg"
        else: target_ext = f".{target_ext}"

        if not self.state.files:
            self.files_summary.controls.append(
                ft.Container(
                    content=ft.Text("파일을 추가하면 여기에서 출력 파일명을 미리 확인할 수 있습니다.", color=COLORS["text_muted"]),
                    padding=SPACING["md"],
                )
            )
        for f in self.state.files[:10]:
            self.files_summary.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f.name, size=11, color=COLORS["text_soft"], overflow="ellipsis", expand=True),
                        ft.Icon(ft.Icons.ARROW_FORWARD, size=12, color=COLORS["line"]),
                        ft.Text(f.with_suffix(target_ext).name, size=11, color=COLORS["accent"], expand=True),
                    ], spacing=SPACING["sm"]),
                    padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
                    border_radius=RADII["sm"],
                    bgcolor=COLORS["surface_alt"] if len(self.files_summary.controls) % 2 == 0 else "transparent",
                )
            )
        
        if len(self.state.files) > 10:
            self.files_summary.controls.append(ft.Text(f"... +{len(self.state.files)-10} more", size=10, color=COLORS["text_soft"]))
        
        count = len(self.state.files)
        self.btn_convert.content = ft.Text(f"{count}개 파일 변환")
        self.lbl_file_count.value = f"입력 파일 {count}개"
        self.summary_text.value = f"출력 형식: {self.state.target_format}"
        destination = "원본 폴더" if not self.state.save_to_folder else "Converted_Images 폴더"
        self.destination_text.value = f"저장 위치: {destination}"
        self.btn_convert.disabled = not bool(self.state.files) or self.state.is_converting
        self.page.update()

    def on_format_change(self, e):
        self.state.target_format = e.control.value
        self.update_file_list()

    def on_save_folder_toggle(self, e):
        self.state.save_to_folder = e.control.value
        self.update_file_list()

    def on_resize_toggle(self, e):
        self.state.resize_enabled = e.control.value
        if self.resize_combo is not None:
            self.resize_combo.disabled = not e.control.value
        self.page.update()

    def on_pick_files(self, _):
        if self.file_picker is not None:
            files = self.file_picker.pick_files(
                allow_multiple=True,
                file_type=ft.FilePickerFileType.IMAGE,
            )
            self._consume_files(files)

    def on_file_result(self, e):
        self._consume_files(getattr(e, "files", None))

    def _consume_files(self, files):
        if not files:
            return
        known = {str(path.resolve()) for path in self.state.files}
        for file in files:
            path = Path(file.path)
            if not path.exists():
                continue
            resolved = str(path.resolve())
            if resolved in known:
                continue
            self.state.files.append(path)
            known.add(resolved)
        self.update_file_list()

    def on_clear_files(self, _):
        self.state.files.clear()
        self.update_file_list()

    def on_convert_click(self, _):
        if self.state.is_converting: return
        
        self.state.is_converting = True
        self.btn_convert.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.status_text.value = "변환 준비 중..."
        self.page.update()

        resize_px = int(self.state.resize_size) if self.state.resize_enabled else None
        
        self.service.convert_batch(
            files=self.state.files,
            target_fmt=self.state.target_format,
            resize_size=resize_px,
            save_to_folder=self.state.save_to_folder,
            delete_original=self.state.delete_original,
            on_progress=self.handle_progress,
            on_complete=self.handle_complete
        )

    def handle_progress(self, progress, completed, total):
        self.progress_bar.value = progress
        self.status_text.value = f"처리 중 {completed}/{total}"
        self.page.update()

    def handle_complete(self, success_count, errors):
        self.state.is_converting = False
        self.btn_convert.disabled = False
        self.status_text.value = "변환 완료"
        
        msg = f"{success_count}개 이미지를 변환했습니다."
        if errors:
            msg += f"\n\n오류 {len(errors)}건:\n" + "\n".join(errors[:5])
        
        def close_dialog(e):
            self.page.dialog.open = False
            self.page.update()
            if not errors:
                self.page.window_close()

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("변환 완료"),
            content=ft.Text(msg),
            actions=[ft.TextButton("확인", on_click=close_dialog)],
        )
        self.page.dialog.open = True
        self.page.update()

def start_app(initial_files: List[str]):
    app = ImageConvertFletApp(initial_files)
    ft.app(target=app.main)
