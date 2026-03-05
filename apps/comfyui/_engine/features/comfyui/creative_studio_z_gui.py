
import customtkinter as ctk
import threading
import sys
import io
import random
import time
import json
import os
from pathlib import Path
from PIL import Image
import webbrowser

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from features.comfyui.premium import PremiumComfyWindow, Colors, Fonts, GlassFrame, PremiumLabel, ActionButton, PremiumScrollableFrame
from utils.gui_lib import THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from features.comfyui.core.wrappers import registry
from features.comfyui.ui.widgets import ValueSliderWidget, PromptStackWidget
from utils.ai_helper import refine_text_ai
from utils.i18n import t

class CanvasToolbar(ctk.CTkFrame):
    """Floating toolbar for the image viewport."""
    def __init__(self, master, callbacks, **kwargs):
        super().__init__(master, fg_color="#000", corner_radius=20, height=40, width=220, **kwargs)
        self.callbacks = callbacks
        self._build_tools()

    def _build_tools(self):
        tools = [
            ("🧱", "grid"), ("🔍", "zoom"), ("📂", "folder"), ("💾", "save")
        ]
        for icon, cmd in tools:
            btn = ctk.CTkButton(self, text=icon, width=35, height=35, fg_color="transparent", 
                               hover_color="#333", command=self.callbacks.get(cmd), corner_radius=15)
            btn.pack(side="left", padx=5, pady=2)

class CreativeStudioGUI(PremiumComfyWindow):
    def __init__(self):
        super().__init__(title=t("comfyui.creative_studio_z.title"), width=1360, height=950)
        
        # Core Architecture
        self.wrapper = registry.get_by_key("z_turbo")
        self.widgets = {}
        
        # State
        self.is_processing = False
        self.current_image = None
        
        self._setup_layout()

    def _setup_layout(self):
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=0, minsize=480) # Sidebar Force Width
        self.content_area.grid_columnconfigure(1, weight=1) # Viewport

        # --- SIDEBAR (Fixed Width, Split Layout) ---
        self.sidebar = GlassFrame(self.content_area, width=480)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        self.sidebar.grid_propagate(False)
        
        # 1. FIXED CONFIG HEADER
        self.config_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.config_header.pack(fill="x", padx=15, pady=15)
        self._build_config_section(self.config_header)

        # Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#333").pack(fill="x", padx=15)

        # 2. SCROLLABLE PROMPT BODY
        self.scroll_body = PremiumScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_body.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.prompt_widget = PromptStackWidget(self.scroll_body, t("comfyui.creative_studio_z.prompt_layers"), on_refine_handler=self._on_ai_refine)
        
        # 3. FIXED ACTION FOOTER
        self.action_footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.action_footer.pack(fill="x", side="bottom", padx=15, pady=15)
        self._build_ignite_section(self.action_footer)

        # --- VIEWPORT ---
        self.viewport = GlassFrame(self.content_area)
        self.viewport.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        
        self.preview_label = ctk.CTkLabel(self.viewport, text=t("comfyui.creative_studio_z.engine_ready"), font=Fonts.HEADER, text_color=Colors.TEXT_TERTIARY)
        self.preview_label.pack(fill="both", expand=True)

        self.toolbar = CanvasToolbar(self.viewport, callbacks={
            "grid": self._not_implemented, "zoom": self._not_implemented,
            "folder": self.open_output_folder, "save": self.save_current
        })
        self.toolbar.place(relx=0.5, rely=0.92, anchor="center")

    def _build_config_section(self, parent):
        PremiumLabel(parent, text=t("comfyui.creative_studio_z.config"), style="header").pack(anchor="w", pady=(0, 10))
        
        # Resolution Combo
        row1 = ctk.CTkFrame(parent, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        PremiumLabel(row1, text=t("comfyui.creative_studio_z.resolution"), style="small").pack(side="left")
        self.combo_res = ctk.CTkComboBox(row1, values=["1024x1024", "896x1152", "1152x896", "768x768"], width=180,
                                         fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, border_color=THEME_DROPDOWN_BTN)
        self.combo_res.pack(side="right")
        
        # Sliders
        self.widgets["steps"] = ValueSliderWidget(parent, t("comfyui.creative_studio_z.steps"), {"from": 1, "to": 50, "res": 1, "default": 4})
        self.widgets["cfg"] = ValueSliderWidget(parent, t("comfyui.creative_studio_z.cfg"), {"from": 1, "to": 20, "res": 0.1, "default": 2.0})
        self.widgets["batch_size"] = ValueSliderWidget(parent, t("comfyui.creative_studio_z.batch_size"), {"from": 1, "to": 8, "res": 1, "default": 1})

    def _on_ai_refine(self, layer_widget):
        original = layer_widget.get_text()
        if not original: return
        layer_widget.btn_refine.configure(text="⏳", state="disabled")
        self.status_badge.set_status(t("comfyui.creative_studio_z.ai_polishing"), "active")
        
        def _cb(res, err=None):
            self.after(0, lambda: layer_widget.btn_refine.configure(text="✨", state="normal"))
            if res:
                self.after(0, lambda: layer_widget.set_text(res))
                self.after(0, lambda: self.status_badge.set_status(t("comfyui.creative_studio_z.ai_enhanced"), "success") )
            else:
                self.after(0, lambda: self.status_badge.set_status(t("comfyui.creative_studio_z.ai_failed"), "error"))

        refine_text_ai(original, type="prompt", callback=_cb)

    def _build_ignite_section(self, parent):
        # Options
        opts = ctk.CTkFrame(parent, fg_color="transparent")
        opts.pack(fill="x", pady=(0, 10))
        
        self.widgets["upscale"] = ctk.CTkCheckBox(opts, text=t("comfyui.creative_studio_z.upscale"), font=Fonts.BODY, fg_color=Colors.ACCENT_PRIMARY)
        self.widgets["upscale"].pack(side="left", padx=5)
        
        self.widgets["rembg"] = ctk.CTkCheckBox(opts, text=t("comfyui.creative_studio_z.rembg"), font=Fonts.BODY, fg_color=Colors.ACCENT_PURPLE)
        self.widgets["rembg"].pack(side="left", padx=5)

        # Action Row
        action_row = ctk.CTkFrame(parent, fg_color="transparent")
        action_row.pack(fill="x")

        self.btn_ignite = ActionButton(action_row, text=t("comfyui.creative_studio_z.ignite"), variant="magic", height=55, command=self.start_generation)
        self.btn_ignite.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_web = ctk.CTkButton(action_row, text="🌐", width=55, height=55, fg_color=Colors.BG_CARD, 
                                    border_width=1, border_color="#333", hover_color="#444", 
                                    command=self.open_webui)
        self.btn_web.pack(side="right")

    def open_webui(self):
        # 1. Generate Current Workflow JSON
        try:
            prompt = self.prompt_widget.get_combined_text()
            if not prompt: prompt = "" # Allow empty for viewing

            w, h = map(int, self.combo_res.get().split("x"))
            ui_values = {
                "prompt": prompt,
                "width": w, "height": h,
                "steps": int(self.widgets["steps"].get_value()),
                "cfg": float(self.widgets["cfg"].get_value()),
                "batch_size": int(self.widgets["batch_size"].get_value()),
                "upscale": self.widgets["upscale"].get(),
                "rembg": self.widgets["rembg"].get(),
                "seed": random.randint(0, 2**32-1)
            }
            
            with open(src_dir / self.wrapper.workflow_path, 'r') as f: 
                base_workflow = json.load(f)
            
            # Apply values to get final API format (or standard format)
            # Note: wrapper.apply_values returns API format usually. 
            # For WebUI 'Load', we ideally want the standard format (with node positions).
            # If our stored workflow.json HAS positions, we should just update values in place if possible.
            # But wrapper.apply_values might destroy structure if it's designed for API.
            # Let's try to just dump the wrapper's result for now, or raw load + patch.
            
            # Let's trust apply_values to return a valid ComfyUI JSON.
            final_workflow = self.wrapper.apply_values(base_workflow, ui_values)
            
            json_str = json.dumps(final_workflow, indent=2)
            
            # 2. Copy to Clipboard
            self.clipboard_clear()
            self.clipboard_append(json_str)
            self.update() # Keep clipboard
            
            # 3. Notify
            self.status_badge.set_status(t("comfyui.common.copied"), "success")
            print("[INFO] Workflow JSON copied to clipboard. Paste in WebUI to view.")
            
        except Exception as e:
            print(f"[WARN] Could not generate workflow for WebUI: {e}")

        # 4. Open Browser
        url = self.get_server_url()
        webbrowser.open(url)

    def start_generation(self):
        if self.is_processing: return
        
        prompt = self.prompt_widget.get_combined_text()
        if not prompt: return
        
        w, h = map(int, self.combo_res.get().split("x"))
        ui_values = {
            "prompt": prompt,
            "width": w, "height": h,
            "steps": int(self.widgets["steps"].get_value()),
            "cfg": float(self.widgets["cfg"].get_value()),
            "batch_size": int(self.widgets["batch_size"].get_value()),
            "upscale": self.widgets["upscale"].get(),
            "rembg": self.widgets["rembg"].get(),
            "seed": random.randint(0, 2**32-1)
        }
        
        self.is_processing = True
        self.btn_ignite.configure(state="disabled", text=t("comfyui.common.synthesizing"))
        self.status_badge.set_status(t("comfyui.creative_studio_z.igniting"), "active")
        
        threading.Thread(target=self._run_thread, args=(ui_values,), daemon=True).start()

    def _run_thread(self, val):
        try:
            with open(src_dir / self.wrapper.workflow_path, 'r') as f: workflow = json.load(f)
            workflow = self.wrapper.apply_values(workflow, val)
            outputs = self.client.generate_image(workflow)
            images = []
            if outputs:
                for nid, result in outputs.items():
                    for b in result: images.append(Image.open(io.BytesIO(b)))
            
            processed = self.wrapper.post_process(images, val)
            self.after(0, lambda: self._on_success(processed))
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _on_success(self, images):
        self.is_processing = False
        self.btn_ignite.configure(state="normal", text=t("comfyui.creative_studio_z.ignite"))
        self.status_badge.set_status(t("comfyui.common.success"), "success")
        if images:
            self.current_image = images[-1]
            ctk_img = ctk.CTkImage(self.current_image, size=(800, 800 * self.current_image.height // self.current_image.width))
            self.preview_label.configure(image=ctk_img, text="")

    def _on_error(self, msg):
        self.is_processing = False
        self.btn_ignite.configure(state="normal", text="Retry")
        self.status_badge.set_status(t("comfyui.common.error"), "error")
        print(msg)

    def open_output_folder(self): os.startfile(Path.home() / "Pictures" / "ContextUp_Exports")
    def save_current(self): pass
    def _not_implemented(self): pass

if __name__ == "__main__":
    app = CreativeStudioGUI()
    app.mainloop()
