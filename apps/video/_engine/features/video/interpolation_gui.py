"""
Video Frame Interpolation GUI
Interface for FFmpeg-based frame interpolation.
"""
import os
import sys
import threading
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from pathlib import Path

import sys
from pathlib import Path

# --- BOOTSTRAP ---
def _bootstrap():
    root = Path(__file__).resolve().parent
    while not (root / 'src').exists() and root.parent != root:
        root = root.parent
    if (root / 'src').exists():
        sys.path.append(str(root / 'src')) # Add src to path
        try: import utils.bootstrap
        except: pass
_bootstrap()
# -----------------

from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from utils.i18n import t
from core.logger import setup_logger

logger = setup_logger("video_interp_gui")

class VideoInterpApp(BaseWindow):
    def __init__(self):
        super().__init__(title=t("video_interp_gui.title"), width=500, height=500, icon_name="video_frame_interp")
        
        # State
        self.input_path = None
        self.is_processing = False
        self.process = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # --- Input Section ---
        input_frame = ctk.CTkFrame(self.main_frame, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        input_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(input_frame, text=t("video_interp_gui.input_video")).pack(anchor="w", padx=10, pady=(5,0))
        
        file_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        file_row.pack(fill="x", padx=5, pady=5)
        
        self.entry_input = ctk.CTkEntry(file_row, placeholder_text="Select video file...")
        self.entry_input.pack(side="left", fill="x", expand=True, padx=(5,5))
        
        ctk.CTkButton(file_row, text=t("common.browse"), width=80, 
                     fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                     command=self.browse_input).pack(side="right", padx=5)

        self.method_var = ctk.StringVar(value="ffmpeg")

        # --- Options Section ---
        self.opts_frame = ctk.CTkFrame(self.main_frame, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        self.opts_frame.pack(fill="x", padx=10, pady=10)
        
        # Multiplier
        ctk.CTkLabel(self.opts_frame, text=t("video_interp_gui.options")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        self.mult_var = ctk.StringVar(value="2x")
        self.opt_mult = ctk.CTkOptionMenu(self.opts_frame, variable=self.mult_var,
                                        values=["2x", "4x", "Target 30fps", "Target 60fps"])
        self.opt_mult.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        # Quality (FFmpeg only)
        self.lbl_quality = ctk.CTkLabel(self.opts_frame, text="Quality Mode:")
        self.lbl_quality.grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        self.quality_var = ctk.StringVar(value="mci")
        self.opt_quality = ctk.CTkOptionMenu(self.opts_frame, variable=self.quality_var,
                                           values=["mci (High Quality)", "blend (Fast)"])
        self.opt_quality.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # --- Progress ---
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=10, pady=20)
        
        self.lbl_status = ctk.CTkLabel(self.progress_frame, text=t("common.ready"))
        self.lbl_status.pack(anchor="w", padx=5)
        
        self.progress = ctk.CTkProgressBar(self.progress_frame)
        self.progress.pack(fill="x", padx=5, pady=5)
        self.progress.set(0)
        
        # --- Actions ---
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.btn_run = ctk.CTkButton(btn_frame, text=t("video_interp_gui.start"), height=40, 
                                   font=("", 14, "bold"), 
                                   fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                                   command=self.start_processing)
        self.btn_run.pack(fill="x", padx=5)

    def browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")])
        if path:
            self.input_path = path
            self.entry_input.delete(0, "end")
            self.entry_input.insert(0, path)

    def update_options(self):
        self.lbl_quality.grid()
        self.opt_quality.grid()
        self.opt_mult.configure(values=["2x", "4x", "Target 30fps", "Target 60fps"])

    def start_processing(self):
        if self.is_processing: return
        
        input_path = self.entry_input.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video.")
            return
            
        self.is_processing = True
        self.btn_run.configure(state="disabled", text="Processing...")
        self.progress.set(0)
        self.lbl_status.configure(text="Initializing...")
        
        threading.Thread(target=self.run_thread, args=(input_path,), daemon=True).start()

    def run_thread(self, input_path):
        try:
            method = self.method_var.get()
            mult = self.mult_var.get()
            
            # Parse multiplier/target
            target_arg = ""
            if "Target" in mult:
                target_arg = f"--fps {mult.split()[1].replace('fps','')}"
            else:
                target_arg = f"--multiplier {mult.replace('x','')}"

            if method == "ffmpeg":
                quality = "mci" if "mci" in self.quality_var.get() else "blend"
                script = "ai_standalone/frame_interpolation.py" # Reuse existing script
                
                # We need to run it and capture output for progress
                # For now, just run it
                cmd = [sys.executable, f"src/scripts/{script}", input_path, 
                       "--method", quality] + target_arg.split()
                
                self.run_process(cmd)

        except Exception as e:
            self.update_status(f"Error: {e}")
        finally:
            self.is_processing = False
            self.after(0, lambda: self.btn_run.configure(state="normal", text="Start Interpolation"))

    def run_process(self, cmd):
        # Helper to run subprocess and update progress (basic)
        self.update_status("Processing with FFmpeg...")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        for line in process.stdout:
            # Parse FFmpeg progress here if possible
            # frame=  123 fps= 12 ...
            if "frame=" in line:
                self.update_status(line.strip())
        
        process.wait()
        if process.returncode == 0:
            self.update_status("Done!")
            self.progress.set(1.0)
        else:
            self.update_status("Failed.")

    def update_status(self, msg):
        self.after(0, lambda: self.lbl_status.configure(text=msg))

if __name__ == "__main__":
    app = VideoInterpApp()
    app.mainloop()
