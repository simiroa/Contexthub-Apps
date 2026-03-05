
import customtkinter as ctk
import threading
import sys
import random
import time
import json
import io
import os
import subprocess
from pathlib import Path
import webbrowser

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from features.comfyui.premium import PremiumComfyWindow, Colors, Fonts, GlassFrame, PremiumLabel, ActionButton, PremiumScrollableFrame
from utils.gui_lib import THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from features.comfyui.workflow_wrappers import WorkflowRegistry
from features.comfyui.ui.widgets import ValueSliderWidget, PromptStackWidget, ComboboxWidget, CheckboxWidget, LoraStackWidget, ImageParamWidget, SketchPadWidget, TextInputWidget, SeedWidget, AspectRatioWidget
from utils.i18n import t

class CreativeStudioAdvancedGUI(PremiumComfyWindow):
    def __init__(self):
        super().__init__(title=t("comfyui.creative_studio_advanced.title"), width=1380, height=950)
        
        self.registry = WorkflowRegistry()
        self.current_wrapper = None
        self.widgets = {} # key -> widget_obj
        
        self._setup_layout()
        
    def _setup_layout(self):
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=0, minsize=480) # Compact Standard
        self.content_area.grid_columnconfigure(1, weight=1) # Viewport

        # --- SIDEBAR ---
        self.sidebar = GlassFrame(self.content_area, width=480)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        self.sidebar.grid_propagate(False)
        
        self.scroll = PremiumScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=5, pady=5) # Tight padding

        # 1. Preset Selector
        con = self._add_section_header(self.scroll, t("comfyui.creative_studio_advanced.workflow_engine"), is_highlight=True)
        names = self.registry.get_all_names()
        self.combo_preset = ctk.CTkComboBox(con, values=names, height=35, command=self._on_wrapper_selected,
                                              fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, border_color=THEME_DROPDOWN_BTN)
        self.combo_preset.pack(fill="x", padx=10, pady=10)
        
        # 2. Dynamic Params Area
        self.param_area = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.param_area.pack(fill="both", expand=True)

        # 3. Action Footer
        self.footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.footer.pack(fill="x", side="bottom", padx=15, pady=15)

        self.btn_ignite = ActionButton(self.footer, text=t("comfyui.creative_studio_advanced.ignite_btn"), variant="magic", height=50, command=self.start_generation)
        self.btn_ignite.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_web = ctk.CTkButton(self.footer, text="🌐", width=50, height=50, fg_color=Colors.BG_CARD, 
                                    border_width=1, border_color="#333", hover_color="#444", 
                                    command=self.open_webui)
        self.btn_web.pack(side="right")

        # --- VIEWPORT ---
        self.viewport = GlassFrame(self.content_area)
        self.viewport.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        self.preview_label = ctk.CTkLabel(self.viewport, text=t("comfyui.creative_studio_advanced.ready"), font=Fonts.HEADER)
        self.preview_label.pack(fill="both", expand=True)

        if names:
            self.combo_preset.set(names[0])
            self._on_wrapper_selected(names[0])

    def _on_wrapper_selected(self, name):
        wrapper = self.registry.get_by_name(name)
        if not wrapper: return
        self.current_wrapper = wrapper
        
        # Clear & Rebuild
        for child in self.param_area.winfo_children(): child.destroy()
        self.widgets = {}
        
        ui_defs = wrapper.get_ui_definition()
        for d in ui_defs:
            if d.type == "slider":
                self.widgets[d.key] = ValueSliderWidget(self.param_area, d.label, d.options or {})
            elif d.type == "text":
                self.widgets[d.key] = PromptStackWidget(self.param_area, d.label, 
                                                      on_refine_handler=lambda w: self._on_ai_refine(w))
            elif d.type in ["combo", "ckpt"]:
                vals = d.options if isinstance(d.options, list) else [] # Handle list options directly
                if not vals and d.type == "ckpt": vals = ["sd_xl_base_1.0.safetensors", "v1-5-pruned-emaonly.ckpt"] # Fallback
                self.widgets[d.key] = ComboboxWidget(self.param_area, d.label, vals, default=d.default)
            elif d.type == "checkbox":
                self.widgets[d.key] = CheckboxWidget(self.param_area, d.label, default=d.default)
            elif d.type == "lora":
                self.widgets[d.key] = LoraStackWidget(self.param_area, d.label)
            elif d.type == "image":
                self.widgets[d.key] = ImageParamWidget(self.param_area, d.label)
            elif d.type == "sketch":
                self.widgets[d.key] = SketchPadWidget(self.param_area, d.label)
            elif d.type == "string":
                self.widgets[d.key] = TextInputWidget(self.param_area, d.label, default=d.default)
            elif d.type == "seed":
                self.widgets[d.key] = SeedWidget(self.param_area, d.label, default=d.default)
            elif d.type == "aspect":
                self.widgets[d.key] = AspectRatioWidget(self.param_area, d.label, default=d.default)
            elif d.type == "video":
                self.widgets[d.key] = ImageParamWidget(self.param_area, d.label) # Re-use Media Widget

    def _on_ai_refine(self, layer_widget):
        from utils.ai_helper import refine_text_ai
        original = layer_widget.get_text()
        if not original: return
        layer_widget.btn_refine.configure(text="⏳", state="disabled")
        
        def _cb(res, err=None):
            self.after(0, lambda: layer_widget.btn_refine.configure(text="✨", state="normal"))
            if res: self.after(0, lambda: layer_widget.set_text(res))
        
        refine_text_ai(original, type="prompt", callback=_cb)

    def _add_section_header(self, parent, text, is_highlight=False):
        color = Colors.ACCENT_PRIMARY if is_highlight else "#333"
        f = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=8, border_width=1, border_color=color)
        f.pack(fill="x", pady=5)
        
        lbl = PremiumLabel(f, text=text, style="header")
        lbl.configure(text_color=color)
        lbl.pack(anchor="w", padx=10, pady=(10, 5))
        return f

    def open_webui(self):
        # 1. Generate JSON & Copy
        try:
            if not self.current_wrapper: return
            wf_path = src_dir / self.current_wrapper.workflow_path
            with open(wf_path, 'r') as f: workflow_json = json.load(f)
            
            ui_values = {}
            for k, v in self.widgets.items():
                if isinstance(v, PromptStackWidget): ui_values[k] = v.get_combined_text()
                else: ui_values[k] = v.get_value()

            final_workflow = self.current_wrapper.apply_values(workflow_json, ui_values)
            json_str = json.dumps(final_workflow, indent=2)
            
            self.clipboard_clear()
            self.clipboard_append(json_str)
            self.update()
            
            # self.status_badge.set_status("Copied to Clipboard", "success") 
            # (Note: Advanced GUI doesn't have status badge easily accessible yet in this simplified class, maybe add later)
            print("Workflow copied to clipboard.")
            
        except Exception as e:
            print(f"Error copying workflow: {e}")

        # 2. Open
        url = self.get_server_url()
        webbrowser.open(url)

    def start_generation(self):
        if not self.current_wrapper: return
        
        # 1. Load Base Workflow JSON
        wf_path = src_dir / self.current_wrapper.workflow_path
        with open(wf_path, 'r') as f: workflow_json = json.load(f)
        
        # 2. Gather values from widgets
        ui_values = {}
        for k, v in self.widgets.items():
            if isinstance(v, PromptStackWidget): ui_values[k] = v.get_combined_text()
            else: ui_values[k] = v.get_value()
        
        # 3. Delegate injection to Wrapper
        final_workflow = self.current_wrapper.apply_values(workflow_json, ui_values) # Returns API format
        
        # 4. Execute...
        print(f"Executing wrapped workflow: {self.current_wrapper.name}")
        # Need client integration here, but for now just print

if __name__ == "__main__":
    app = CreativeStudioAdvancedGUI()
    app.mainloop()
