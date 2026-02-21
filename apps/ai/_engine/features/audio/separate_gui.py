"""
Audio Separation GUI using Demucs.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import threading
import subprocess
import sys
import os

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/audio -> src
sys.path.append(str(src_dir))

from utils.i18n import t
from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from utils.audio_player import AudioPlayer
from utils.ai_runner import kill_process_tree

def _is_headless():
    return os.environ.get("CTX_HEADLESS") == "1" or os.environ.get("CTX_CAPTURE_MODE") == "1"

class AudioSeparateGUI(BaseWindow):
    def __init__(self, target_path=None, demo=False):
        super().__init__(title=t("audio_separate_gui.title"), width=650, height=620, icon_name="audio_separate_stems")
        
        self.demo_mode = demo or _is_headless()
        self.target_path = target_path
        self.files = []
        self.process = None
        self.is_running = False
        self.player = AudioPlayer()
        self.result_files = []
        
        if self.demo_mode:
            self.files = [Path("demo_audio.mp3")]
        elif target_path:
            selection = get_selection_from_explorer(target_path)
            if not selection:
                selection = [target_path]
            
            audio_exts = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac', '.wma'}
            self.files = [Path(p) for p in selection if Path(p).suffix.lower() in audio_exts]
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        count = len(self.files)
        if count > 0:
            header_text = t("audio_separate_gui.header_sep").format(count)
        else:
            header_text = t("audio_separate_gui.header_default")
        self.add_header(header_text)
        
        # 0. File List (TOP - Fixed)
        file_list_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        file_list_container.pack(fill="x", padx=20, pady=(0, 10))
        
        if not self.files:
            ctk.CTkButton(file_list_container, text=t("audio_separate_gui.select_files"), command=self.select_files).pack(pady=10)
        else:
             f_frame = ctk.CTkFrame(file_list_container, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
             f_frame.pack(fill="x", pady=5)
             for f in self.files[:3]:
                 ctk.CTkLabel(f_frame, text="  📄 " + f.name, anchor="w").pack(fill="x", padx=10, pady=2)
             if len(self.files) > 3:
                 ctk.CTkLabel(f_frame, text=f"  ... and {len(self.files)-3} more", text_color="gray", font=("", 11)).pack(anchor="w", padx=10, pady=(0, 5))

        # Main Scrollable Area for Options and Log
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=0)

        # Options Container
        opt_frame = ctk.CTkFrame(self.scroll_frame, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        opt_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(opt_frame, text=t("audio_separate_gui.extraction_settings"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Grid layout for options
        grid = ctk.CTkFrame(opt_frame, fg_color="transparent")
        grid.pack(fill="x", padx=15, pady=5)
        
        # Model
        ctk.CTkLabel(grid, text=t("audio_separate_gui.model")).grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.model_var = ctk.StringVar(value="htdemucs")
        ctk.CTkComboBox(grid, variable=self.model_var, values=["htdemucs", "htdemucs_ft", "mdx_extra_q", "hdemucs_mmi"],
                        fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER).grid(row=0, column=1, sticky="e", pady=5, padx=5)
        
        # Format
        ctk.CTkLabel(grid, text=t("audio_separate_gui.output_format")).grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.format_var = ctk.StringVar(value="mp3")
        ctk.CTkComboBox(grid, variable=self.format_var, values=["wav", "mp3", "flac"],
                        fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER).grid(row=1, column=1, sticky="e", pady=5, padx=5)
        
        # Separation Mode
        ctk.CTkLabel(grid, text=t("audio_separate_gui.separation_mode")).grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.mode_var = ctk.StringVar(value="all")
        ctk.CTkComboBox(grid, variable=self.mode_var, values=["All Stems (4)", "Vocals vs Backing (2)"],
                        fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER).grid(row=2, column=1, sticky="e", pady=5, padx=5)

        # Progress & Log
        self.log_area = ctk.CTkTextbox(self.scroll_frame, height=100)
        self.log_area.pack(fill="x", padx=10, pady=10)
        
        self.progress = ctk.CTkProgressBar(self.main_frame)
        self.progress.pack(fill="x", padx=20, pady=5)
        self.progress.set(0)
        
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", padx=20, pady=10)
        
        self.btn_run = ctk.CTkButton(btn_frame, text=t("audio_separate_gui.start_separation"), command=self.start_separation, fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
        self.btn_run.pack(side="right", padx=5)
        self.btn_close = ctk.CTkButton(btn_frame, text=t("common.close"), command=self.cancel_or_close)
        self.btn_close.pack(side="right", padx=5)

    def select_files(self):
        files = filedialog.askopenfilenames()
        if files: 
            self.files = [Path(f) for f in files]
            self.create_widgets() # Rebuild to show files (simple reload)

    def log(self, msg):
        self.log_area.insert("end", msg + "\n")
        self.log_area.see("end")

    def cancel_or_close(self):
        if self.is_running and self.process:
            kill_process_tree(self.process)
            self.is_running = False
            self.log(t("audio_separate_gui.cancelled"))
        else:
            self.on_closing()

    def start_separation(self):
        if not self.files: 
            messagebox.showwarning(t("audio_separate_gui.no_files_title"), t("audio_separate_gui.no_files_body"))
            return
        self.is_running = True
        self.btn_run.configure(state="disabled")
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        try:
            python_exe = sys.executable
            if getattr(sys, 'frozen', False):
                # If running from inside ContextHub Host's python, we might need a better way to find demucs
                # but for now we assume it's in the env.
                pass
            # Options
            model = self.model_var.get()
            fmt = self.format_var.get()
            mode = self.mode_var.get()
            
            for i, path in enumerate(self.files):
                if not self.is_running: break
                
                self.log(t("audio_separate_gui.processing").format(path.name))
                
                output_dir = path.parent / "Separated_Audio"
                cmd = [python_exe, "-m", "demucs", "-n", model, "-o", str(output_dir), str(path)]
                
                if fmt == "mp3": cmd.append("--mp3")
                elif fmt == "flac": cmd.append("--flac")
                # default is wav
                
                if "2" in mode:
                    cmd.append("--two-stems=vocals")
                
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in self.process.stdout:
                    if not self.is_running: break
                    self.after(0, lambda l=line: self.log(l.strip()))
                self.process.wait()
                self.process = None
                self.progress.set((i+1)/len(self.files))
                
            self.log(t("audio_separate_gui.all_completed"))
        except Exception as e:
            self.log(f"Error: {e}")
        self.is_running = False
        self.after(0, lambda: self.btn_run.configure(state="normal"))

    def on_closing(self):
        if self.process:
            kill_process_tree(self.process)
        self.player.stop()
        self.destroy()

def separate_audio(target_path=None):
    try:
        app = AudioSeparateGUI(target_path)
        app.mainloop()
    except Exception as e:
        messagebox.showerror(t("common.error"), str(e))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        anchor = sys.argv[1]
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("audio_separate", anchor, timeout=0.2) is None:
            sys.exit(0)
    separate_audio(sys.argv[1] if len(sys.argv) > 1 else None)
