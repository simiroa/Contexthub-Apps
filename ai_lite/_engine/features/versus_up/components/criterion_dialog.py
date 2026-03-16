import flet as ft
from contexthub.ui.flet.tokens import COLORS, SPACING

class CriterionDialog(ft.AlertDialog):
    def __init__(self, criterion_data, on_save, on_delete, on_close):
        super().__init__()
        self.c_data = criterion_data
        self.on_save = on_save
        self.on_delete = on_delete
        self.on_close = on_close
        
        cid, pid, name, c_type, weight, direction, ignore, unit = (
            self.c_data + (None,)*(8-len(self.c_data))
        )
        self.cid = cid
        self.name_val = name or ""
        self.weight_val = weight if weight is not None else 1.0
        self.dir_val = direction or 1
        self.ign_val = bool(ignore)
        self.unit_val = unit or ""
        
        self.title = ft.Text(f"Settings: {self.name_val}", size=16, weight=ft.FontWeight.BOLD)
        self.build_dialog()

    def build_dialog(self):
        self.name_field = ft.TextField(label="Name", value=self.name_val, autofocus=True, text_size=12)
        self.unit_field = ft.TextField(label="Unit", value=self.unit_val, text_size=12)
        
        self.weight_label = ft.Text(f"Weight: {self.weight_val:.1f}", size=12, color=COLORS["text_muted"])
        self.weight_slider = ft.Slider(
            min=0.1, max=5.0, value=self.weight_val, divisions=49,
            on_change=lambda e: self._on_weight_change(e.control.value)
        )
        
        self.dir_radio = ft.RadioGroup(
            value=str(self.dir_val),
            content=ft.Column([
                ft.Radio(value="1", label="Higher is better (+)"),
                ft.Radio(value="-1", label="Lower is better (−)")
            ], spacing=4)
        )
        
        self.ignore_check = ft.Checkbox(label="Ignore in scoring", value=self.ign_val)
        
        self.content = ft.Column([
            self.name_field, self.unit_field,
            ft.Divider(height=1, color=COLORS["line"]),
            self.weight_label, self.weight_slider,
            self.dir_radio, self.ignore_check
        ], tight=True, spacing=SPACING["sm"], width=300)
        
        self.actions = [
            ft.TextButton("Delete", on_click=lambda e: self.on_delete(self.cid), style=ft.ButtonStyle(color=COLORS["danger"])),
            ft.Container(expand=True),
            ft.TextButton("Cancel", on_click=lambda e: self.on_close(self)),
            ft.ElevatedButton("Save", on_click=self._do_save, bgcolor=COLORS["accent"], color=COLORS["text"])
        ]

    def _on_weight_change(self, val):
        self.weight_label.value = f"Weight: {val:.1f}"
        self.weight_label.update()

    def _do_save(self, e):
        self.on_save(
            self.cid,
            self.name_field.value or self.name_val,
            self.weight_slider.value,
            int(self.dir_radio.value),
            int(self.ignore_check.value),
            self.unit_field.value
        )
