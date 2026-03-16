import flet as ft
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING

class AIVisionDialog(ft.AlertDialog):
    def __init__(self, page, product_name, image_path, criteria_list, values_map, on_sync, on_close):
        super().__init__()
        self.page = page
        self.product_name = product_name
        self.image_path = image_path
        self.criteria_list = criteria_list
        self.values_map = values_map
        self.on_sync = on_sync
        self.on_close = on_close
        
        self.title = ft.Text(f"AI Scan: {product_name}", size=16, weight=ft.FontWeight.BOLD)
        self.extracted_data = {}
        self.comparison_rows = []
        
        self.build_dialog()

    def build_dialog(self):
        self.status_text = ft.Text("Analyzing image with Ollama Vision...", color=COLORS["accent"], size=12)
        self.progress_bar = ft.ProgressBar(width=400, color=COLORS["accent"])
        
        self.results_table = ft.Column(spacing=4, scroll=ft.ScrollMode.ADAPTIVE, height=200, visible=False)
        
        self.content = ft.Column(
            [
                ft.Row([
                    ft.Image(src=self.image_path, width=150, height=100, fit=ft.ImageFit.COVER, border_radius=RADII["sm"]),
                    ft.Column([
                        ft.Text("Extraction Comparison", weight=ft.FontWeight.W_600),
                        self.status_text,
                    ], spacing=4)
                ], vertical_alignment="start"),
                self.progress_bar,
                self.results_table,
            ],
            tight=True, width=500
        )
        
        self.sync_btn = ft.ElevatedButton("Keep / Replace Selected", on_click=self._do_sync, disabled=True, bgcolor=COLORS["accent"], color=COLORS["text"])
        self.actions = [
            ft.TextButton("Cancel", on_click=lambda e: self.on_close(self)),
            self.sync_btn
        ]

    def set_results(self, result_json):
        self.extracted_data = result_json
        self.status_text.value = "Analysis complete. Review suggestions below:"
        self.status_text.color = COLORS["success"]
        self.progress_bar.visible = False
        
        # Build comparison grid
        self.comparison_rows = []
        header = ft.Row([
            ft.Text("Criterion", size=10, weight=ft.FontWeight.BOLD, width=120),
            ft.Text("Current", size=10, weight=ft.FontWeight.BOLD, width=80),
            ft.Text("Detected", size=10, weight=ft.FontWeight.BOLD, width=80),
            ft.Text("Action", size=10, weight=ft.FontWeight.BOLD, width=80),
        ], spacing=10)
        
        detected_items = result_json.get("criteria", [])
        table_controls = [header, ft.Divider(height=1, color=COLORS["line"])]
        
        for item in detected_items:
            name = item.get("name")
            detected_val = str(item.get("value", ""))
            
            # Find matching criterion ID
            matching_crit = next((c for c in self.criteria_list if c[2].lower() == name.lower()), None)
            current_val = ""
            cid = None
            if matching_crit:
                cid = matching_crit[0]
                # Assuming pid is handled outside or passed? Let's assume we need to know pid.
                # Actually, values_map should have it. Handle this logic in set_results.
            
            # Action: 0=Keep, 1=Replace
            action_dropdown = ft.Dropdown(
                value="1" if detected_val != "" else "0",
                options=[ft.dropdown.Option("0", "Keep"), ft.dropdown.Option("1", "Replace")],
                width=80, text_size=10, content_padding=2,
            )
            
            row = ft.Row([
                ft.Text(name, size=11, width=120, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text("(empty)" if not current_val else current_val, size=11, width=80, color=COLORS["text_muted"]),
                ft.Text(detected_val, size=11, width=80, color=COLORS["accent"], weight=ft.FontWeight.BOLD),
                action_dropdown
            ], spacing=10, vertical_alignment="center")
            
            table_controls.append(row)
            self.comparison_rows.append({"name": name, "cid": cid, "val": detected_val, "dropdown": action_dropdown})

        self.results_table.controls = table_controls
        self.results_table.visible = True
        self.sync_btn.disabled = False
        self.update()

    def _do_sync(self, e):
        sync_data = []
        for r in self.comparison_rows:
            if r["dropdown"].value == "1":
                sync_data.append({"name": r["name"], "cid": r["cid"], "value": r["val"]})
        self.on_sync(self, sync_data)
