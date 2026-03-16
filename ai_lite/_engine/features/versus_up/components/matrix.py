import os
import flet as ft
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING

_CELL_W = 120  # More compact
_LABEL_W = 140
PRODUCT_COLORS = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#06B6D4"]

def _highlight_color(kind):
    if kind == "best":
        return "#064E3B", "#10B981"  # Deep green bg, bright green border
    if kind == "worst":
        return "#7F1D1D", "#EF4444"  # Deep red bg, bright red border
    return COLORS["field_bg"], COLORS["line"]

class Matrix(ft.Container):
    def __init__(
        self,
        state,
        on_rename_product,
        on_delete_product,
        on_pick_image,
        on_scan_product,  # New AI Scan button
        on_criterion_settings,
        on_update_value,
    ):
        super().__init__()
        self.state = state
        self.on_rename_product = on_rename_product
        self.on_delete_product = on_delete_product
        self.on_pick_image = on_pick_image
        self.on_scan_product = on_scan_product
        self.on_criterion_settings = on_criterion_settings
        self.on_update_value = on_update_value
        
        self.expand = True
        self.padding = SPACING["md"]
        self.bgcolor = COLORS["surface"]
        self.border = ft.border.all(1, COLORS["line"])
        self.border_radius = RADII["md"]
        
        self.build_matrix()

    def build_matrix(self):
        if not self.state.products and not self.state.criteria:
            self.content = ft.Container(
                alignment=ft.alignment.Alignment(0, 0),
                content=ft.Text("Add products and criteria to begin", color=COLORS["text_muted"])
            )
            return

        # Header Row
        header_cells = [ft.Container(width=_LABEL_W, height=130)]
        for i, p in enumerate(self.state.products):
            score = self.state.scores.get(p[0], 0.0)
            color = PRODUCT_COLORS[i % len(PRODUCT_COLORS)]
            
            # Thumbnail / Scan Overlay
            if p[3] and os.path.exists(p[3]):
                img_control = ft.Image(src=p[3], width=_CELL_W-16, height=60, fit=ft.ImageFit.COVER, border_radius=RADII["sm"])
            else:
                img_control = ft.Container(
                    width=_CELL_W-16, height=60, bgcolor=COLORS["app_bg"], border_radius=RADII["sm"],
                    content=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=COLORS["text_soft"])
                )

            header_cells.append(
                ft.Container(
                    width=_CELL_W,
                    content=ft.Column(
                        [
                            ft.Text(f"{score:.1f}", size=20, weight=ft.FontWeight.BOLD, color=color),
                            ft.TextField(
                                value=p[2], text_size=11, bgcolor="transparent", border_color="transparent",
                                text_align="center", content_padding=2,
                                on_submit=lambda e, pid=p[0]: self.on_rename_product(pid, e.control.value),
                            ),
                            ft.Stack([
                                ft.Container(content=img_control, on_click=lambda e, pid=p[0]: self.on_pick_image(pid)),
                                ft.IconButton(
                                    icon=ft.Icons.DOCUMENT_SCANNER_OUTLINED, 
                                    icon_size=16, icon_color=COLORS["accent"],
                                    tooltip="AI Scan",
                                    bgcolor=COLORS["surface"],
                                    right=4, bottom=4,
                                    on_click=lambda e, pid=p[0]: self.on_scan_product(pid)
                                )
                            ])
                        ],
                        horizontal_alignment="center", spacing=4
                    )
                )
            )

        header_row = ft.Row(header_cells, spacing=SPACING["xs"], scroll=ft.ScrollMode.AUTO)

        # Data Rows
        data_rows = []
        for cr in self.state.criteria:
            cid = cr[0]
            unit = cr[7] if len(cr) > 7 else ""
            is_ignored = bool(cr[6]) if len(cr) > 6 else False
            
            label = ft.Container(
                width=_LABEL_W,
                padding=ft.padding.symmetric(vertical=4),
                on_click=lambda e, c=cr: self.on_criterion_settings(c),
                content=ft.Column([
                    ft.Text(cr[2], size=11, weight=ft.FontWeight.W_600, color=COLORS["text_muted"] if is_ignored else COLORS["text"]),
                    ft.Text(f"w:{cr[4]:.1f} {unit}", size=9, color=COLORS["text_soft"])
                ], spacing=0, tight=True)
            )
            
            row_cells = [label]
            for p in self.state.products:
                pid = p[0]
                val = self.state.values_map.get((pid, cid), "")
                hl = self.state.cell_highlights.get((pid, cid))
                bg, border_c = _highlight_color(hl)
                
                row_cells.append(
                    ft.TextField(
                        value=str(val), width=_CELL_W, text_size=11, bgcolor=bg, border_color=border_c,
                        border_width=1.5 if hl else 1, text_align="center", content_padding=5,
                        suffix=ft.Text(unit, size=9, color=COLORS["text_soft"]) if unit else None,
                        on_submit=lambda e, _p=pid, _c=cid: self.on_update_value(_p, _c, e.control.value),
                    )
                )
            data_rows.append(ft.Row(row_cells, spacing=SPACING["xs"], scroll=ft.ScrollMode.AUTO))

        self.content = ft.Column(
            [header_row, ft.Divider(color=COLORS["line"], height=1)] + data_rows,
            spacing=SPACING["xs"], scroll=ft.ScrollMode.ADAPTIVE
        )
