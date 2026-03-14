import flet as ft
from pathlib import Path
from .video_audio_state import VideoAudioState
from .video_audio_service import VideoAudioService
from utils.i18n import t

def create_video_audio_app(state: VideoAudioState):
    def video_audio_app(page: ft.Page):
        page.title = "Video Audio Tools"
        page.window_width = 650
        page.window_height = 700
        page.theme_mode = ft.ThemeMode.DARK
        
        service = VideoAudioService(state, on_update=lambda **kwargs: update_ui(**kwargs))

        # UI Components
        file_list = ft.ListView(expand=1, spacing=5, padding=10)
        for f in state.files:
            file_list.controls.append(ft.Text(f.name, size=12, color=ft.colors.GREY_400))

        # Tabs
        tab_bar = ft.Tabs(
            selected_index=0 if state.mode == "extract" else (1 if state.mode == "remove" else 2),
            on_change=lambda e: on_tab_change(e.control.selected_index),
            tabs=[
                ft.Tab(text="Extract Audio"),
                ft.Tab(text="Remove Audio"),
                ft.Tab(text="Separate (Voice/BGM)")
            ]
        )

        extract_options = ft.Column([
            ft.Text("Select Output Format:", weight="bold"),
            ft.RadioGroup(
                content=ft.Row([
                    ft.Radio(value="MP3", label="MP3 (Compressed)"),
                    ft.Radio(value="WAV", label="WAV (Lossless)")
                ]),
                value=state.extract_format,
                on_change=lambda e: setattr(state, "extract_format", e.data)
            )
        ], visible=state.mode == "extract")

        remove_options = ft.Column([
            ft.Text("Remove audio track from video files", color=ft.colors.GREY_500),
            ft.Text("Video codec will be copied (fast)", color=ft.colors.GREY_600, size=11)
        ], visible=state.mode == "remove")

        separate_options = ft.Column([
            ft.Text("Separate Voice and BGM", weight="bold"),
            ft.Text("Uses simple frequency filtering", color=ft.colors.GREY_600, size=11),
            ft.RadioGroup(
                content=ft.Row([
                    ft.Radio(value="Voice", label="Extract Voice"),
                    ft.Radio(value="BGM", label="Extract BGM")
                ]),
                value=state.separate_mode,
                on_change=lambda e: setattr(state, "separate_mode", e.data)
            )
        ], visible=state.mode == "separate")

        progress_bar = ft.ProgressBar(value=0, visible=False)
        status_text = ft.Text(state.status_text, color=ft.colors.GREY_500, size=12)

        def on_tab_change(index):
            if index == 0: state.mode = "extract"
            elif index == 1: state.mode = "remove"
            elif index == 2: state.mode = "separate"
            
            extract_options.visible = (state.mode == "extract")
            remove_options.visible = (state.mode == "remove")
            separate_options.visible = (state.mode == "separate")
            
            action_btn.content.value = f"{state.mode.capitalize()} Audio" if state.mode != "separate" else "Process Separation"
            update_ui()

        def start_processing(e):
            service.start_processing()

        def cancel_processing(e):
            if state.is_processing:
                service.cancel_processing()
            else:
                page.window_close()

        action_btn = ft.ElevatedButton(
            content=ft.Text("Extract Audio", weight="bold"),
            on_click=start_processing,
            bgcolor=ft.colors.BLUE_700,
            color=ft.colors.WHITE,
            expand=True,
            height=45,
            tooltip="Start processing"
        )

        cancel_btn = ft.OutlinedButton(
            content=ft.Text(t("common.cancel")),
            on_click=cancel_processing,
            expand=True,
            height=45,
            tooltip=t("common.cancel")
        )

        def update_ui(finished=False, success=0, total=0, errors=None):
            action_btn.disabled = state.is_processing
            progress_bar.visible = state.is_processing or state.progress_value > 0
            progress_bar.value = state.progress_value
            status_text.value = state.status_text
            
            if finished:
                msg = f"Processed {success}/{total} files."
                if errors:
                    msg += "\n\nErrors:\n" + "\n".join(errors[:5])
                
                def close_dlg(e):
                    dlg.open = False
                    page.update()
                    if not errors:
                        page.window_close()

                dlg = ft.AlertDialog(
                    title=ft.Text(t("common.success") if not errors else t("common.error")),
                    content=ft.Text(msg),
                    actions=[ft.TextButton("OK", on_click=close_dlg)]
                )
                page.dialog = dlg
                dlg.open = True
            
            page.update()

        # Initial button text
        action_btn.content.value = f"{state.mode.capitalize()} Audio" if state.mode != "separate" else "Process Separation"

        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text(f"Video Audio Tools ({len(state.files)})", size=20, weight="bold"),
                    ft.Container(file_list, height=120, border=ft.border.all(1, ft.colors.GREY_800), border_radius=5),
                    tab_bar,
                    ft.Container(
                        content=ft.Column([
                            extract_options,
                            remove_options,
                            separate_options
                        ]),
                        padding=10,
                        border=ft.border.all(1, ft.colors.GREY_800),
                        border_radius=5,
                        height=150
                    ),
                    ft.Checkbox(label="Save to new folder", value=state.save_to_folder, on_change=lambda e: setattr(state, "save_to_folder", e.control.value)),
                    ft.VerticalDivider(height=10),
                    progress_bar,
                    status_text,
                    ft.Row([cancel_btn, action_btn], spacing=10)
                ], spacing=15),
                padding=20
            )
        )

    return video_audio_app
