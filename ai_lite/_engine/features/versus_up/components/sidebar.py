import flet as ft
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING

class Sidebar(ft.Container):
    def __init__(
        self,
        state,
        on_project_select,
        on_delete_project,
        on_new_project,
        on_open_ai,
        on_export,
    ):
        super().__init__()
        self.state = state
        self.on_project_select = on_project_select
        self.on_delete_project = on_delete_project
        self.on_new_project = on_new_project
        self.on_open_ai = on_open_ai
        self.on_export = on_export
        
        self.width = 180  # Slant and compact
        self.bgcolor = COLORS["surface"]
        self.border = ft.border.only(right=ft.BorderSide(1, COLORS["line"]))
        self.padding = ft.padding.all(SPACING["sm"])
        self.visible = state.sidebar_visible
        
        self.build_sidebar()

    def build_sidebar(self):
        sidebar_list = ft.Column(
            spacing=2,
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
        )
        for p in self.state.projects:
            is_active = p[0] == self.state.current_project_id
            sidebar_list.controls.append(
                ft.Container(
                    bgcolor=COLORS["accent"] if is_active else "transparent",
                    border_radius=RADII["sm"],
                    padding=ft.padding.symmetric(horizontal=SPACING["xs"], vertical=6),
                    on_click=lambda e, pid=p[0]: self.on_project_select(pid),
                    content=ft.Row(
                        [
                            ft.Text(
                                p[1],
                                size=12,
                                color=COLORS["text"] if is_active else COLORS["text_muted"],
                                expand=True,
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                icon_size=12,
                                icon_color=COLORS["text_muted"],
                                on_click=lambda e, pid=p[0]: self.on_delete_project(pid),
                                style=ft.ButtonStyle(padding=0),
                            ) if is_active else ft.Container(),
                        ],
                        vertical_alignment="center",
                        spacing=4,
                    ),
                )
            )

        self.content = ft.Column(
            [
                ft.Text(
                    "PROJECTS",
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS["text_muted"],
                ),
                sidebar_list,
                ft.Divider(color=COLORS["line"], height=1),
                ft.Column(
                    spacing=SPACING["xs"],
                    controls=[
                        ft.TextButton(
                            "New Project",
                            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                            on_click=self.on_new_project,
                            style=ft.ButtonStyle(color=COLORS["text"], text_style=ft.TextStyle(size=12)),
                        ),
                        ft.TextButton(
                            "AI Vision",
                            icon=ft.Icons.AUTO_AWESOME_OUTLINED,
                            on_click=self.on_open_ai,
                            style=ft.ButtonStyle(color=COLORS["accent"], text_style=ft.TextStyle(size=12)),
                        ),
                        ft.TextButton(
                            "Export Report",
                            icon=ft.Icons.DESCRIPTION_OUTLINED,
                            on_click=self.on_export,
                            style=ft.ButtonStyle(color=COLORS["text_soft"], text_style=ft.TextStyle(size=12)),
                        ),
                    ],
                ),
            ],
            spacing=SPACING["sm"],
            expand=True,
        )
