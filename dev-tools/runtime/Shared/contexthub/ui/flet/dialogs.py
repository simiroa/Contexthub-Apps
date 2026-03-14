from __future__ import annotations

from contexthub.ui.flet.tokens import COLORS, RADII, SPACING, WINDOWS


def build_progress_dialog(ft, title: str, hint: str, on_cancel=None):
    title_text = ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=COLORS["text"])
    hint_text = ft.Text(hint, color=COLORS["text_muted"])
    progress = ft.ProgressBar(width=320, value=0, color=COLORS["accent"], bgcolor=COLORS["line"])
    actions = []
    if on_cancel is not None:
        actions.append(ft.TextButton("Cancel", on_click=on_cancel))
    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["surface_alt"],
        shape=ft.RoundedRectangleBorder(radius=RADII["lg"]),
        content=ft.Container(
            width=WINDOWS["dialog"]["width"],
            padding=SPACING["xl"],
            content=ft.Column(
                tight=True,
                controls=[
                    title_text,
                    hint_text,
                    progress,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=actions,
                    ),
                ],
            ),
        ),
    )
    return {
        "dialog": dialog,
        "title": title_text,
        "hint": hint_text,
        "progress": progress,
    }
