from __future__ import annotations

import flet as ft

from contexthub.ui.flet.layout import action_bar, apply_button_sizing
from contexthub.ui.flet.theme import configure_page
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING

from versus_up_service import VersusUpService
from versus_up_state import VersusUpState


PRESETS = {
    "Smartphone": [("Price", "number", 1, -1, "$"), ("Display Size", "number", 2, 1, '"'), ("Battery", "number", 2, 1, "mAh")],
    "Travel": [("Daily Cost", "number", 1, -1, "$"), ("Safety", "number", 3, 1, "/10"), ("Food Score", "number", 3, 1, "/10")],
    "Computer": [("Price", "number", 1, -1, "$"), ("CPU Perf", "number", 3, 1, "pts"), ("RAM", "number", 2, 1, "GB")],
    "Empty": [],
}


class VersusUpFletApp:
    def __init__(self):
        self.service = VersusUpService()
        self.state = VersusUpState()

    def run(self):
        ft.app(target=self.main)

    def _ensure_seed_data(self):
        if not self.service.get_projects():
            self.service.db.insert_dummy_data()

    def _load_projects(self):
        self.state.projects = self.service.get_projects()
        if self.state.projects and not self.state.current_project_id:
            self.state.current_project_id = self.state.projects[0][0]
        self._load_project_data()

    def _load_project_data(self):
        if not self.state.current_project_id:
            self.state.products = []
            self.state.criteria = []
            self.state.values_map = {}
            self.state.scores = {}
            return
        products, criteria, values = self.service.get_project_data(self.state.current_project_id)
        self.state.products = products
        self.state.criteria = criteria
        self.state.values_map = {(value[0], value[1]): value[2] or "" for value in values}
        self.state.scores, self.state.crit_stats = self.service.calculate_scores(
            self.state.products,
            self.state.criteria,
            self.state.values_map,
        )

    def main(self, page: ft.Page):
        self.page = page
        configure_page(page, "VersusUp", window_profile="desktop")
        page.bgcolor = COLORS["app_bg"]
        self._ensure_seed_data()
        self._load_projects()
        self.build_ui()

    def build_ui(self):
        self.page.clean()
        title = self.state.get_current_project_name()

        summary = ft.Container(
            padding=SPACING["lg"],
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["line"]),
            border_radius=RADII["lg"],
            content=ft.Column(
                spacing=SPACING["sm"],
                controls=[
                    ft.Text("VersusUp", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Compare products, plans, or purchases with editable criteria and live score totals.",
                        color=COLORS["text_muted"],
                    ),
                    ft.Text(
                        f"Project: {title} · Products: {len(self.state.products)} · Criteria: {len(self.state.criteria)}",
                        color=COLORS["text_muted"],
                    ),
                ],
            ),
        )

        project_dropdown = ft.Dropdown(
            label="Project",
            value=str(self.state.current_project_id) if self.state.current_project_id else None,
            options=[ft.dropdown.Option(str(project[0]), project[1]) for project in self.state.projects],
            bgcolor=COLORS["field_bg"],
            border_color=COLORS["line"],
            expand=True,
        )
        project_dropdown.on_change = self._on_project_change

        toolbar = ft.Row(
            [
                project_dropdown,
                apply_button_sizing(ft.OutlinedButton("New Project", on_click=self._on_new_project), "compact"),
                apply_button_sizing(ft.OutlinedButton("Add Product", on_click=self._on_add_product), "compact"),
                apply_button_sizing(ft.OutlinedButton("Add Criterion", on_click=self._on_add_criterion), "compact"),
                apply_button_sizing(ft.TextButton("Export Markdown", on_click=self._on_export), "compact"),
            ],
            wrap=True,
            spacing=SPACING["sm"],
            run_spacing=SPACING["sm"],
        )

        product_column = ft.Column(spacing=SPACING["sm"], scroll=ft.ScrollMode.ADAPTIVE)
        for product in self.state.products:
            score = self.state.scores.get(product[0], 0.0)
            name_field = ft.TextField(
                value=product[2],
                bgcolor=COLORS["field_bg"],
                border_color=COLORS["line"],
                on_submit=lambda e, pid=product[0]: self._rename_product(pid, e.control.value),
            )
            product_column.controls.append(
                ft.Container(
                    padding=SPACING["md"],
                    bgcolor=COLORS["surface"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["md"],
                    content=ft.Column(
                        spacing=SPACING["sm"],
                        controls=[
                            ft.Row(
                                [
                                    ft.Text(f"Score {score:.2f}", color=COLORS["accent"], weight=ft.FontWeight.BOLD),
                                    ft.Container(expand=True),
                                    ft.IconButton(ft.Icons.DELETE_OUTLINE, on_click=lambda e, pid=product[0]: self._delete_product(pid)),
                                ]
                            ),
                            name_field,
                        ],
                    ),
                )
            )
        if not product_column.controls:
            product_column.controls.append(ft.Text("No products yet.", color=COLORS["text_muted"]))

        criteria_column = ft.Column(spacing=SPACING["sm"], scroll=ft.ScrollMode.ADAPTIVE)
        for criterion in self.state.criteria:
            direction = "Higher is better" if len(criterion) <= 5 or criterion[5] != -1 else "Lower is better"
            unit = criterion[7] if len(criterion) > 7 and criterion[7] else "-"
            criteria_column.controls.append(
                ft.Container(
                    padding=SPACING["md"],
                    bgcolor=COLORS["surface"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["md"],
                    content=ft.Row(
                        [
                            ft.Column(
                                expand=True,
                                spacing=4,
                                controls=[
                                    ft.Text(criterion[2], weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{direction} · Unit: {unit} · Weight: {criterion[4]}", color=COLORS["text_muted"], size=12),
                                ],
                            ),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, on_click=lambda e, cid=criterion[0]: self._delete_criterion(cid)),
                        ]
                    ),
                )
            )
        if not criteria_column.controls:
            criteria_column.controls.append(ft.Text("No criteria yet.", color=COLORS["text_muted"]))

        matrix_header = [ft.Container(width=180, content=ft.Text("Criterion", weight=ft.FontWeight.BOLD))]
        for product in self.state.products:
            matrix_header.append(ft.Container(width=140, content=ft.Text(product[2], weight=ft.FontWeight.BOLD)))

        matrix_rows = ft.Column(spacing=SPACING["sm"], scroll=ft.ScrollMode.ADAPTIVE)
        for criterion in self.state.criteria:
            row_controls: list[ft.Control] = [ft.Container(width=180, content=ft.Text(criterion[2]))]
            for product in self.state.products:
                value = self.state.values_map.get((product[0], criterion[0]), "")
                field = ft.TextField(
                    value=str(value),
                    width=140,
                    bgcolor=COLORS["field_bg"],
                    border_color=COLORS["line"],
                    on_submit=lambda e, pid=product[0], cid=criterion[0]: self._update_value(pid, cid, e.control.value),
                )
                row_controls.append(field)
            matrix_rows.controls.append(ft.Row(row_controls, spacing=SPACING["sm"], wrap=False))
        if not matrix_rows.controls:
            matrix_rows.controls.append(ft.Text("Add criteria and products to begin comparison.", color=COLORS["text_muted"]))

        status_text = ft.Text("Ready", color=COLORS["text_muted"], size=12)
        reset_btn = ft.OutlinedButton("Reset All", on_click=self._on_reset_all)
        close_btn = ft.ElevatedButton("Close", on_click=lambda e: self.page.window_close(), bgcolor=COLORS["accent"], color=COLORS["text"])

        body = ft.Column(
            expand=True,
            spacing=SPACING["md"],
            controls=[
                summary,
                toolbar,
                ft.Row(
                    expand=True,
                    spacing=SPACING["md"],
                    controls=[
                        ft.Container(
                            expand=2,
                            padding=SPACING["md"],
                            bgcolor=COLORS["surface"],
                            border=ft.border.all(1, COLORS["line"]),
                            border_radius=RADII["md"],
                            content=ft.Column([ft.Text("Products", size=16, weight=ft.FontWeight.BOLD), product_column], expand=True),
                        ),
                        ft.Container(
                            expand=2,
                            padding=SPACING["md"],
                            bgcolor=COLORS["surface"],
                            border=ft.border.all(1, COLORS["line"]),
                            border_radius=RADII["md"],
                            content=ft.Column([ft.Text("Criteria", size=16, weight=ft.FontWeight.BOLD), criteria_column], expand=True),
                        ),
                    ],
                ),
                ft.Container(
                    padding=SPACING["md"],
                    bgcolor=COLORS["surface"],
                    border=ft.border.all(1, COLORS["line"]),
                    border_radius=RADII["md"],
                    content=ft.Column(
                        spacing=SPACING["sm"],
                        controls=[
                            ft.Text("Comparison Matrix", size=16, weight=ft.FontWeight.BOLD),
                            ft.Row(matrix_header, spacing=SPACING["sm"], wrap=False),
                            ft.Container(content=matrix_rows, height=260),
                        ],
                    ),
                ),
                action_bar(status=status_text, primary=close_btn, secondary=[reset_btn]),
            ],
        )

        self.page.add(ft.Container(expand=True, bgcolor=COLORS["app_bg"], padding=SPACING["lg"], content=body))
        self.page.update()

    def _refresh(self):
        self._load_projects()
        self.build_ui()

    def _on_project_change(self, e: ft.ControlEvent):
        try:
            self.state.current_project_id = int(e.control.value)
        except (TypeError, ValueError):
            self.state.current_project_id = None
        self._refresh()

    def _on_new_project(self, e: ft.ControlEvent):
        name_field = ft.TextField(label="Project Name", autofocus=True)
        preset_dropdown = ft.Dropdown(label="Preset", value="Empty", options=[ft.dropdown.Option(name) for name in PRESETS.keys()])

        def create_project(ev: ft.ControlEvent):
            if not name_field.value:
                return
            self.service.create_project(name_field.value, preset_dropdown.value, PRESETS.get(preset_dropdown.value, []))
            self.page.close(dialog)
            self.state.current_project_id = None
            self._refresh()

        dialog = ft.AlertDialog(
            title=ft.Text("New Comparison Project"),
            content=ft.Column([name_field, preset_dropdown], tight=True),
            actions=[ft.TextButton("Cancel", on_click=lambda ev: self.page.close(dialog)), ft.ElevatedButton("Create", on_click=create_project)],
        )
        self.page.open(dialog)

    def _on_add_product(self, e: ft.ControlEvent):
        if not self.state.current_project_id:
            return
        self.service.add_product(self.state.current_project_id, f"Product {len(self.state.products) + 1}")
        self._refresh()

    def _on_add_criterion(self, e: ft.ControlEvent):
        if not self.state.current_project_id:
            return
        self.service.add_criterion(self.state.current_project_id, f"Criterion {len(self.state.criteria) + 1}")
        self._refresh()

    def _rename_product(self, product_id: int, name: str):
        if not name:
            return
        self.service.db.update_product_name(product_id, name)
        self._refresh()

    def _delete_product(self, product_id: int):
        self.service.delete_product(product_id)
        self._refresh()

    def _delete_criterion(self, criterion_id: int):
        self.service.delete_criterion(criterion_id)
        self._refresh()

    def _update_value(self, product_id: int, criterion_id: int, value: str):
        self.service.update_value(product_id, criterion_id, value)
        self._refresh()

    def _on_export(self, e: ft.ControlEvent):
        if not self.state.current_project_id:
            return
        project = next((item for item in self.state.projects if item[0] == self.state.current_project_id), None)
        if not project:
            return
        markdown = self.service.export_project(project, self.state.products, self.state.criteria, self.state.values_map)
        self.page.set_clipboard(markdown)
        self.page.open(ft.SnackBar(ft.Text("Markdown copied to clipboard.")))

    def _on_reset_all(self, e: ft.ControlEvent):
        self.service.db.clear_all_data()
        self.service.db.insert_dummy_data()
        self.state.current_project_id = None
        self._refresh()


def open_versus_up_flet():
    VersusUpFletApp().run()


if __name__ == "__main__":
    open_versus_up_flet()
