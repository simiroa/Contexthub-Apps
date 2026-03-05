
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import sys
import os
import shutil
import time
from pathlib import Path

# Fix module imports
project_root = Path(__file__).resolve().parents[3] 
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.append(str(src_path))

from features.comfyui.premium import PremiumComfyWindow, Colors, Fonts, GlassFrame, PremiumLabel, ActionButton
from utils.gui_lib import THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from features.comfyui import workflow_utils
from manager.helpers.comfyui_service import ComfyUIService
from utils.i18n import t

class SeedVR2_GUI(PremiumComfyWindow):
    def __init__(self):
        super().__init__(title=t("comfyui.seedvr2.title"), width=420, height=580)
        self.video_path = None
        self.is_video = False
        
        # Use standard theme color for status badge
        self.status_badge.configure(fg_color="#121212")
        self._setup_ui()
        
    def _setup_ui(self):
        # Centered Card Layout
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)
        
        # Main Card - Reduce padding for compact UI
        self.card = GlassFrame(self.content_area)
        self.card.grid(row=0, column=0, sticky="nsew", padx=15, pady=(5, 15))
        self.card.grid_columnconfigure(0, weight=1)
        
        # 1. Hero Select - Reduced padding
        self.hero_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.hero_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        self.btn_file = ActionButton(self.hero_frame, text=t("comfyui.seedvr2.open_file"), variant="secondary", height=50, command=self.select_file)
        self.btn_file.pack(fill="x")
        
        self.lbl_file_info = PremiumLabel(self.hero_frame, text=t("comfyui.seedvr2.no_file"), style="secondary")
        self.lbl_file_info.pack(pady=5)
        
        # 2. Settings Grid - Reduced padding
        self.settings = ctk.CTkFrame(self.card, fg_color="transparent")
        self.settings.pack(fill="x", padx=20, pady=5)
        
        # Model
        row1 = ctk.CTkFrame(self.settings, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        PremiumLabel(row1, text=t("comfyui.seedvr2.model"), style="body").pack(side="left")
        self.combo_model = ctk.CTkComboBox(row1, values=["seedvr2_ema_7b_sharp_fp16.safetensors"], width=200, height=28,
                                           fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, border_color=THEME_DROPDOWN_BTN)
        self.combo_model.pack(side="right")
        
        # Resolution
        row2 = ctk.CTkFrame(self.settings, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        PremiumLabel(row2, text=t("comfyui.seedvr2.res"), style="body").pack(side="left")
        self.combo_res = ctk.CTkComboBox(row2, values=["1024", "2048", "3840"], width=200, height=28,
                                         fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, border_color=THEME_DROPDOWN_BTN)
        self.combo_res.set("2048")
        self.combo_res.pack(side="right")
        
        # Progress - Reduced padding and standard blue color
        self.progress_bar = ctk.CTkProgressBar(self.card, height=6, progress_color=Colors.THEME_ACCENT)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(25, 5))
        
        # 3. Action - Reduced padding
        self.btn_start = ActionButton(self.card, text=t("comfyui.seedvr2.start"), variant="primary", command=self.start_process, state="disabled")
        self.btn_start.pack(fill="x", padx=20, pady=(10, 20))

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Media", "*.png *.jpg *.mp4 *.mkv")])
        if path:
            self.video_path = path
            self.lbl_file_info.configure(text=t("comfyui.seedvr2.selected", name=os.path.basename(path)))
            self.btn_start.configure(state="normal")
            
            # Auto-detect mode
            ext = os.path.splitext(path)[1].lower()
            self.is_video = ext in ['.mp4', '.mkv', '.avi']

    def start_process(self):
        if not self.video_path: return
        self.btn_start.configure(state="disabled", text=t("comfyui.seedvr2.processing"))
        self.status_badge.set_status(t("comfyui.seedvr2.queued"), "active")
        self.progress_bar.set(0)
        
        threading.Thread(target=self._run_thread, daemon=True).start()

    def _run_thread(self):
        try:
            # Ensure engine
            if not self.client.is_running():
                 service = ComfyUIService()
                 ok, port, _ = service.ensure_running(start_if_missing=True)
                 if ok: self.client.set_active_port(port)

            wf_name = "video_hd.json" if self.is_video else "image_simple.json"
            wf_path = project_root / "ContextUp" / "assets" / "workflows" / "seedvr2" / wf_name
            workflow = workflow_utils.load_workflow(wf_path)
            
            if not workflow: raise Exception("Workflow missing")

            # Input setup
            comfy_in = self.client.comfy_dir / "input"
            comfy_in.mkdir(parents=True, exist_ok=True)
            temp_name = f"uvr_{int(time.time())}{os.path.splitext(self.video_path)[1]}"
            shutil.copy(self.video_path, comfy_in / temp_name)
            
            # Simple updates (Mapping to logic in original file)
            # Assuming util functions handle node search if IDs match standard templates
            # Node 3/1 is Loader, Node 4 is Upscaler
            
            node_loader = "1" if self.is_video else "3"
            workflow_utils.update_node_value(workflow, node_loader, "video" if self.is_video else "image", temp_name)
            
            res = int(self.combo_res.get())
            workflow_utils.update_node_value(workflow, "4", "resolution", res)
            workflow_utils.update_node_value(workflow, "4", "max_resolution", res)
            
            def on_prog(val, max_v):
                self.after(0, lambda v=val/max_v: self.progress_bar.set(v))
                
            self.client.generate_image(workflow, progress_callback=on_prog)
            
            self.after(0, lambda: self.status_badge.set_status(t("comfyui.seedvr2.done"), "success"))
            self.after(0, lambda: messagebox.showinfo(t("comfyui.seedvr2.done"), t("comfyui.seedvr2.complete_msg")))
            
        except Exception as e:
            self.after(0, lambda: self.status_badge.set_status(t("comfyui.common.error"), "error"))
            self.after(0, lambda: messagebox.showerror(t("comfyui.common.error"), str(e)))
        finally:
            self.after(0, lambda: self.btn_start.configure(state="normal", text=t("comfyui.seedvr2.start")))

if __name__ == "__main__":
    app = SeedVR2_GUI()
    app.mainloop()
