import customtkinter as ctk
from tkinter import messagebox, filedialog
from pathlib import Path
import threading
import subprocess
import sys
import os

# Add dependencies to path
current_dir = Path(__file__).resolve().parent
engine_dir = current_dir.parents[2] # standalone -> ai -> features -> _engine
sys.path.append(str(engine_dir))

from utils.gui_lib import BaseWindow, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_CARD, THEME_BORDER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, ModelManagerFrame, FileListFrame
from utils.image_utils import scan_for_images
from utils.ai_runner import run_ai_script, start_ai_script, kill_process_tree
from utils.i18n import t


class UpscaleGUI(BaseWindow):
    def __init__(self, target_path=None):
        super().__init__(title=t("upscale_gui.header"), width=640, height=720, icon_name="image_upscale_ai")
        
        self.target_path = target_path
        self.files = []
        self.current_process = None
        if target_path:
            self.files, count = scan_for_images(target_path)
            
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Header
        count_text = t("upscale_gui.images_count").format(len(self.files)) if self.files else t("upscale_gui.drag_drop")
        self.add_header(f"{t('upscale_gui.header')} {count_text}")
        
        # 1. File List Preview (Prominent at top)
        ctk.CTkLabel(self.main_frame, text=t("upscale_gui.files_label"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=25, pady=(10, 5))
        
        self.file_list = FileListFrame(self.main_frame, self.files, height=130)
        self.file_list.pack(fill="x", padx=25, pady=(0, 10))
        
        if not self.files:
            ctk.CTkButton(self.main_frame, text=t("upscale_gui.select_btn"), command=self.select_files).pack(pady=5)

        # 2. Settings Card
        settings_card = ctk.CTkFrame(self.main_frame, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        settings_card.pack(fill="x", padx=25, pady=10)
        
        # Grid for Settings
        self.var_model = ctk.StringVar(value="RealESRGAN_x4plus")
        self.var_scale = ctk.DoubleVar(value=4.0)
        self.var_face = ctk.BooleanVar(value=False)
        self.var_tile = ctk.IntVar(value=0)
        
        # Scale Row
        scale_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        scale_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(scale_frame, text=t("upscale_gui.upscale_factor") + ":", font=ctk.CTkFont(weight="bold")).pack(side="left")
        radio_frame = ctk.CTkFrame(scale_frame, fg_color="transparent")
        radio_frame.pack(side="right")
        ctk.CTkRadioButton(radio_frame, text="2x", variable=self.var_scale, value=2.0).pack(side="left", padx=10)
        ctk.CTkRadioButton(radio_frame, text="4x", variable=self.var_scale, value=4.0).pack(side="left", padx=10)
        
        # Separator Line
        ctk.CTkFrame(settings_card, height=1, fg_color=THEME_BORDER).pack(fill="x", padx=10)
        
        # Options Row
        opts_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        opts_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkCheckBox(opts_frame, text=t("upscale_gui.face_enhance"), variable=self.var_face).pack(anchor="w")
        ctk.CTkLabel(opts_frame, text="   " + t("upscale_gui.face_hint"), text_color="gray", font=("", 11)).pack(anchor="w")
        
        ctk.CTkCheckBox(opts_frame, text=t("upscale_gui.use_tiling"), variable=self.var_tile, onvalue=512, offvalue=0).pack(anchor="w", pady=(15, 0))

        # 3. Model Manager
        from utils import paths
        model_root = paths.AI_MODELS_DIR / "esrgan"
        self.model_mgr = ModelManagerFrame(self.main_frame, "RealESRGAN / GFPGAN", model_root, download_command=self.download_models, check_callback=self._has_realesrgan_cache)
        self.model_mgr.pack(fill="x", padx=25, pady=10)

        # 4. Progress & Status
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=25, pady=(20, 0))
        
        self.lbl_status = ctk.CTkLabel(self.progress_frame, text=t("upscale_gui.ready"), text_color="gray")
        self.lbl_status.pack(anchor="w")
        
        self.progress = ctk.CTkProgressBar(self.progress_frame)
        self.progress.pack(fill="x", pady=5)
        self.progress.set(0)
        
        # 5. Buttons Row
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", padx=25, pady=25)
        
        self.btn_cancel = ctk.CTkButton(btn_frame, text=t("common.cancel"), command=self.destroy, 
                                        height=45, fg_color="transparent", border_width=1, border_color=THEME_BORDER, text_color=("gray10", "gray90"))
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_run = ctk.CTkButton(btn_frame, text=t("upscale_gui.start_btn"), command=self.start_processing, 
                                     height=45, font=ctk.CTkFont(weight="bold"), fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
        self.btn_run.pack(side="left", fill="x", expand=True)

    def select_files(self):
        paths = filedialog.askopenfilenames(filetypes=[("Images", "*.jpg;*.png;*.webp;*.bmp")])
        if paths:
            self.files = [Path(p) for p in paths]
            self.file_list.set_files(self.files)
            count_text = t("upscale_gui.images_count").format(len(self.files))
            self.add_header(f"{t('upscale_gui.header')} {count_text}")
            # Ensure file list is visible if it was empty
            self.file_list.pack(fill="x", padx=25, pady=(0, 10))

    def _has_realesrgan_cache(self):
        try:
            from utils import paths
            root = paths.REALESRGAN_DIR
            if root.exists() and any(root.glob("*.pth")):
                return True
            return False
        except Exception:
            return False


    def download_models(self):
        """Downloads models via legacy script or direct logic."""
        self.model_mgr.lbl_status.configure(text=t("ai_common.downloading"), text_color="#E67E22")
        self.model_mgr.btn_action.configure(state="disabled")
        
        def _dl():
            # Use upscale.py's check mechanism
            engine_dir = Path(__file__).resolve().parents[2]
            dl_script = engine_dir / "setup" / "download_models.py"
            if not dl_script.exists():
                raise FileNotFoundError(f"Missing download script: {dl_script}")
            cmd = [sys.executable, str(dl_script), "--upscale"]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            success = (proc.returncode == 0)
            output = (proc.stdout or "") + (proc.stderr or "")
            if success:
                 self.main_frame.after(0, lambda: self.model_mgr.check_status())
            else:
                 self.main_frame.after(0, lambda: self.model_mgr.lbl_status.configure(text=t("ai_common.download_failed"), text_color="red"))
            
            self.main_frame.after(0, lambda: self.model_mgr.btn_action.configure(state="normal"))

        threading.Thread(target=_dl, daemon=True).start()

    def start_processing(self):

        if not self.files:
            messagebox.showwarning(t("common.warning"), t("upscale_gui.select_btn"))
            return
            
        self.btn_run.configure(state="disabled", text=t("common.processing"))
        threading.Thread(target=self.run_logic, daemon=True).start()

    def run_logic(self):
        scale = self.var_scale.get()
        face_enhance = self.var_face.get()
        tile = self.var_tile.get()
        
        args = [
            "upscale.py",
        ]
        
        # Add all file paths
        for f in self.files:
            args.append(str(f))
            
        # Add options
        args.extend(["--scale", str(scale)])
        if face_enhance: args.append("--face-enhance")
        if tile > 0: args.extend(["--tile", str(tile)])
        
        self.lbl_status.configure(text=t("upscale_gui.initializing"))
        self.progress.set(0.1)
        
        try:
            from utils.ai_runner import start_ai_script, kill_process_tree
            self.current_process = start_ai_script(*args)
            stdout, _ = self.current_process.communicate()
            success = (self.current_process.returncode == 0)
            self.current_process = None
            
            if success:
                self.progress.set(1.0)
                self.lbl_status.configure(text=t("upscale_gui.completed"))
                self.btn_run.configure(state="normal", text=t("upscale_gui.open_folder"), command=self.open_output_folder)
                messagebox.showinfo(t("common.success"), t("common.success"))
            else:
                self.lbl_status.configure(text=t("upscale_gui.processing_failed"))
                self.btn_run.configure(state="normal", text=t("upscale_gui.retry"), command=self.start_processing)
                messagebox.showerror(t("common.error"), f"{t('upscale_gui.processing_failed')}:\n{stdout}")
                
        except Exception as e:
            self.lbl_status.configure(text=t("upscale_gui.exception"))
            messagebox.showerror(t("common.error"), f"{t('upscale_gui.exception')}: {e}")

    def open_output_folder(self):
        if self.files:
            parent = self.files[0].parent
            os.startfile(parent)

    def on_closing(self):
        from utils.ai_runner import kill_process_tree
        if self.current_process:
            kill_process_tree(self.current_process)
        self.destroy()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        app = UpscaleGUI(sys.argv[1])
    else:
        app = UpscaleGUI()
    app.mainloop()
