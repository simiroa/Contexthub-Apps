from __future__ import annotations

import flet as ft

from contexthub.ui.flet.tokens import COLORS, RADII, SPACING


def min_button_width(kind: str = "primary") -> int:
    widths = {
        "compact": 120,
        "primary": 180,
        "toolbar": 148,
    }
    return widths.get(kind, widths["primary"])


def apply_button_sizing(control: ft.Control, kind: str = "primary") -> ft.Control:
    if hasattr(control, "width") and getattr(control, "width", None) is None:
        control.width = min_button_width(kind)
    if hasattr(control, "height") and getattr(control, "height", None) is None:
        control.height = 44
    return control


def toolbar_row(*controls: ft.Control, expand_tail: bool = True) -> ft.Row:
    row_controls = list(controls)
    if expand_tail:
        row_controls.append(ft.Container(expand=True))
    return ft.Row(
        row_controls,
        wrap=True,
        run_spacing=SPACING["sm"],
        spacing=SPACING["sm"],
        vertical_alignment="center",
    )


def action_bar(
    *,
    status: ft.Control,
    primary: ft.Control,
    progress: ft.Control | None = None,
    secondary: list[ft.Control] | None = None,
) -> ft.Container:
    actions = [apply_button_sizing(primary, "primary")]
    for control in secondary or []:
        actions.insert(0, apply_button_sizing(control, "compact"))

    content = [progress] if progress is not None else []
    content.append(
        ft.Row(
            [
                ft.Container(content=status, expand=True),
                ft.Row(actions, wrap=True, spacing=SPACING["sm"], run_spacing=SPACING["sm"]),
            ],
            alignment="spaceBetween",
            vertical_alignment="center",
        )
    )
    return ft.Container(
        content=ft.Column(content, spacing=SPACING["sm"]),
        padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["md"]),
        bgcolor=COLORS["surface"],
        border_radius=RADII["md"],
        border=ft.border.all(1, COLORS["line"]),
    )
