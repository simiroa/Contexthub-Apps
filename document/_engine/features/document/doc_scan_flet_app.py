from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import List

import cv2
import flet as ft
import numpy as np
from PIL import Image

from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING


@dataclass
class ScanItem:
    path: Path
    image: np.ndarray
    rotation: int = 0
    filter_type: str = "orig"


def _apply_filter(image: np.ndarray, filter_type: str) -> np.ndarray:
    if filter_type == "bw":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
        return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
    if filter_type == "magic":
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        v_eq = clahe.apply(v)
        s_eq = cv2.add(s, 50)
        hsv_eq = cv2.merge((h, s_eq, v_eq))
        colored = cv2.cvtColor(hsv_eq, cv2.COLOR_HSV2BGR)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(colored, -1, kernel)
    return image.copy()


def _render_item(item: ScanItem) -> np.ndarray:
    image = item.image.copy()
    if item.rotation == 90:
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif item.rotation == 180:
        image = cv2.rotate(image, cv2.ROTATE_180)
    elif item.rotation == 270:
        image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return _apply_filter(image, item.filter_type)


def _to_base64(image: np.ndarray) -> str:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    width, height = pil.size
    if width > 760:
        ratio = 760 / width
        pil = pil.resize((int(width * ratio), int(height * ratio)))
    buffer = io.BytesIO()
    pil.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _to_data_url(image: np.ndarray) -> str:
    return f"data:image/png;base64,{_to_base64(image)}"


def start_app(targets: List[str] | None = None):
    def main(page: ft.Page):
        configure_page(page, "Document Scanner", window_profile="wide_canvas")
        page.bgcolor = COLORS["app_bg"]

        valid_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        items: list[ScanItem] = []
        for path in targets or []:
            src = Path(path)
            if src.suffix.lower() not in valid_exts or not src.exists():
                continue
            image = cv2.imdecode(np.fromfile(src, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is not None:
                items.append(ScanItem(path=src, image=image))

        state = {"index": 0 if items else -1}
        thumb_column = ft.Column(spacing=SPACING["sm"], scroll=ft.ScrollMode.ADAPTIVE)
        preview_image = ft.Image(src="", expand=True)
        placeholder = ft.Container(
            expand=True,
            content=ft.Column(
                expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "Load document images from the context menu to preview them here.",
                        color=COLORS["text_muted"],
                        text_align=ft.TextAlign.CENTER,
                    )
                ],
            ),
        )
        filter_group = ft.RadioGroup(
            value="orig",
            content=ft.Column(
                controls=[
                    ft.Radio(value="orig", label="Original"),
                    ft.Radio(value="bw", label="Black & White"),
                    ft.Radio(value="magic", label="Magic Color"),
                ]
            ),
        )
        status_text = ft.Text("Ready", size=12, color=COLORS["text_muted"])

        def current_item() -> ScanItem | None:
            if 0 <= state["index"] < len(items):
                return items[state["index"]]
            return None

        def refresh_thumbs():
            thumb_column.controls = []
            for index, item in enumerate(items):
                thumb_column.controls.append(
                    ft.Container(
                        padding=6,
                        bgcolor=COLORS["surface"] if index == state["index"] else COLORS["surface_alt"],
                        border=ft.border.all(1, COLORS["line"]),
                        border_radius=RADII["sm"],
                        content=ft.Text(item.path.name, size=12),
                        on_click=lambda e, idx=index: select_item(idx),
                    )
                )
            if not thumb_column.controls:
                thumb_column.controls.append(ft.Text("No pages loaded.", color=COLORS["text_muted"]))

        def refresh_preview():
            item = current_item()
            if item is None:
                preview_image.src = ""
                placeholder.visible = True
                status_text.value = "Ready"
            else:
                rendered = _render_item(item)
                preview_image.src = _to_data_url(rendered)
                placeholder.visible = False
                status_text.value = f"{item.path.name} · {item.filter_type}"
                filter_group.value = item.filter_type
            page.update()

        def select_item(index: int):
            state["index"] = index
            refresh_thumbs()
            refresh_preview()

        def rotate_current(delta: int):
            item = current_item()
            if item is None:
                return
            item.rotation = (item.rotation + delta) % 360
            refresh_preview()

        def reset_current(e: ft.ControlEvent):
            item = current_item()
            if item is None:
                return
            item.rotation = 0
            item.filter_type = "orig"
            refresh_preview()

        def on_filter_change(e: ft.ControlEvent):
            item = current_item()
            if item is None:
                return
            item.filter_type = e.control.value
            refresh_preview()

        def save_png(e: ft.ControlEvent):
            item = current_item()
            if item is None:
                return
            output = item.path.with_stem(f"{item.path.stem}_scanned").with_suffix(".png")
            cv2.imencode(".png", _render_item(item))[1].tofile(output)
            status_text.value = f"Saved: {output.name}"
            page.update()

        def save_pdf(e: ft.ControlEvent):
            if not items:
                return
            output = items[0].path.with_stem(f"{items[0].path.stem}_batch_scanned").with_suffix(".pdf")
            pil_images = []
            for item in items:
                rgb = cv2.cvtColor(_render_item(item), cv2.COLOR_BGR2RGB)
                pil_images.append(Image.fromarray(rgb))
            pil_images[0].save(output, "PDF", resolution=100.0, save_all=True, append_images=pil_images[1:])
            status_text.value = f"Saved: {output.name}"
            page.update()

        summary = ft.Container(padding=SPACING["lg"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["lg"], content=ft.Column(spacing=SPACING["sm"], controls=[ft.Text("Document Scanner", size=24, weight=ft.FontWeight.BOLD), ft.Text("Preview pages, rotate, apply simple document filters, and export PNG or merged PDF.", color=COLORS["text_muted"]), ft.Text(f"{len(items)} input files", color=COLORS["text_muted"])]))
        preview_card = ft.Container(expand=True, padding=SPACING["md"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["md"], content=ft.Stack([preview_image, placeholder]))
        tools_card = ft.Container(
            width=320,
            padding=SPACING["md"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["md"],
            content=ft.Column(
                spacing=SPACING["md"],
                controls=[
                    ft.Text("Tools", size=16, weight=ft.FontWeight.BOLD),
                    ft.Row([apply_button_sizing(ft.OutlinedButton("Rotate Left", on_click=lambda e: rotate_current(-90)), "compact"), apply_button_sizing(ft.OutlinedButton("Rotate Right", on_click=lambda e: rotate_current(90)), "compact")], spacing=SPACING["sm"]),
                    apply_button_sizing(ft.OutlinedButton("Reset", on_click=reset_current), "compact"),
                    ft.Text("Filter", size=14, weight=ft.FontWeight.BOLD),
                    filter_group,
                    ft.Text("Save & Export", size=14, weight=ft.FontWeight.BOLD),
                    apply_button_sizing(ft.ElevatedButton("Save PNG", on_click=save_png, bgcolor=COLORS["accent"], color=COLORS["text"]), "primary"),
                    apply_button_sizing(ft.ElevatedButton("Save Merged PDF", on_click=save_pdf, bgcolor=COLORS["accent"], color=COLORS["text"]), "primary"),
                ],
            ),
        )
        filter_group.on_change = on_filter_change

        refresh_thumbs()
        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                padding=SPACING["lg"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["md"],
                    controls=[
                        summary,
                        ft.Row(
                            expand=True,
                            spacing=SPACING["md"],
                            controls=[
                                ft.Container(width=180, padding=SPACING["md"], bgcolor=COLORS["surface"], border=ft.border.all(1, COLORS["line"]), border_radius=RADII["md"], content=ft.Column([ft.Text("Pages", size=16, weight=ft.FontWeight.BOLD), ft.Container(content=thumb_column, expand=True)], expand=True)),
                                preview_card,
                                tools_card,
                            ],
                        ),
                        action_bar(status=status_text, primary=ft.OutlinedButton(content=ft.Text("Close"), on_click=lambda e: page.window_close())),
                    ],
                ),
            )
        )
        refresh_preview()

    ft.app(target=main)
