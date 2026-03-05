"""
Subtitle Generation GUI Tools.
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
src_dir = current_dir.parent.parent  # features/ai -> src
sys.path.append(str(src_dir))

from utils.gui_lib import BaseWindow, THEME_BTN_DANGER, THEME_BTN_DANGER_HOVER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_BORDER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, ModelManagerFrame
from utils.i18n import t
from core.config import MenuConfig

class SubtitleGUI(BaseWindow):
    def __init__(self, target_path=None):
        # Sync Name with Config
        self.tool_name = "ContextUp Subtitle"
        try:
             config = MenuConfig()
             item = config.get_item_by_id("whisper_subtitle")
             if item: self.tool_name = item.get("name", self.tool_name)
        except Exception as e:
             print(f"Config load error: {e}")

        super().__init__(title=self.tool_name, width=640, height=750, icon_name="video_generate_subtitle")
        
        self.files = []
        if target_path:
            self.files.append(Path(target_path))
            
        self.log_visible = True # Default Open
        self.cancel_flag = False
        self.current_process = None
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Check for cached models
        # threading.Thread(target=self.check_cached_models, daemon=True).start()
        


    def create_widgets(self):
        # 1. Header
        self.add_header(f"{self.tool_name} ({len(self.files)})", font_size=20)
        
        # 2. File List
        from utils.gui_lib import FileListFrame
        self.file_scroll = FileListFrame(self.main_frame, self.files, height=180)
        self.file_scroll.pack(fill="x", padx=20, pady=(0, 10))
        
        # 3. Parameters (2-Column Grid)
        param_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        param_frame.pack(fill="x", padx=20, pady=5)
        param_frame.grid_columnconfigure(0, weight=1)
        param_frame.grid_columnconfigure(1, weight=1)
        
        # Left Column: AI Processing
        ai_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        ai_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(ai_frame, text=t("subtitle_gui.ai_processing"), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(5, 5))
        self.create_compact_setting(ai_frame, "Model", ['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3'], "small", "model")
        self.create_compact_setting(ai_frame, "Task", ["transcribe", "translate"], "transcribe", "task")
        self.create_compact_setting(ai_frame, "Device", ["cuda", "cpu"], "cuda", "device")
        self.create_compact_setting(ai_frame, "Language", ["Auto", "en", "ko", "ja", "zh", "es", "fr", "de", "ru", "it"], "Auto", "lang")

        # Model Manager
        from utils import paths
        # Whisper path logic is a bit complex (usually in ~/.cache/whisper), but we can point to our custom one if used
        model_root = paths.WHISPER_DIR 
        
        self.model_mgr = ModelManagerFrame(ai_frame, "Whisper", model_root, download_command=self.download_models, check_callback=self._has_whisper_cache)
        self.model_mgr.pack(fill="x", padx=10, pady=10)

        # Right Column: Output
        out_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        out_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(out_frame, text=t("subtitle_gui.output_deliverables"), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(5, 5))
        
        ctk.CTkLabel(out_frame, text=t("subtitle_gui.output_folder"), font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(5, 0))
        folder_row = ctk.CTkFrame(out_frame, fg_color="transparent")
        folder_row.pack(fill="x", pady=(0, 10))
        
        self.out_dir_var = ctk.StringVar(value="")
        ctk.CTkEntry(folder_row, textvariable=self.out_dir_var, placeholder_text=t("subtitle_gui.default_source_folder"), height=28).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(folder_row, text="...", width=30, height=28, command=self.browse_output_dir).pack(side="right")
        
        ctk.CTkLabel(out_frame, text=t("subtitle_gui.generate_formats"), font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(0, 5))
        fmt_row = ctk.CTkFrame(out_frame, fg_color="transparent")
        fmt_row.pack(fill="x")
        
        self.fmt_srt = ctk.BooleanVar(value=True)
        self.fmt_vtt = ctk.BooleanVar(value=False)
        self.fmt_txt = ctk.BooleanVar(value=False)
        self.fmt_json = ctk.BooleanVar(value=False)
        
        ctk.CTkCheckBox(fmt_row, text="SRT", variable=self.fmt_srt, width=50).pack(side="left")
        ctk.CTkCheckBox(fmt_row, text="VTT", variable=self.fmt_vtt, width=50).pack(side="left")
        ctk.CTkCheckBox(fmt_row, text="TXT", variable=self.fmt_txt, width=50).pack(side="left")
        ctk.CTkCheckBox(fmt_row, text="JSON", variable=self.fmt_json, width=50).pack(side="left")

        # 4. Log Area (Row 3 - Hidden by default)
        self.log_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.log_frame.pack(fill="both", padx=15, pady=5) # Default visible
        
        self.log_area = ctk.CTkTextbox(self.log_frame, font=("Consolas", 10), height=120)
        self.log_area.pack(fill="both", expand=True)

        # 5. Footer (Pack Bottom)
        footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", padx=20, pady=20)

        self.progress_bar = ctk.CTkProgressBar(footer_frame, height=10)
        self.progress_bar.pack(fill="x", pady=(0, 15))
        self.progress_bar.set(0)

        # Options
        opt_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        opt_row.pack(fill="x", pady=(0, 15))
        
        self.btn_toggle_log = ctk.CTkButton(opt_row, text=t("subtitle_gui.hide_log") + " ▲", width=100, height=24, fg_color="transparent", border_width=1, border_color="gray", text_color="gray", command=self.toggle_log)
        self.btn_toggle_log.pack(side="left")
        
        # Buttons
        btn_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_row.pack(fill="x")
        
        self.btn_cancel = ctk.CTkButton(btn_row, text=t("common.cancel"), height=45, fg_color="transparent", border_width=1, border_color=THEME_BORDER, text_color=("gray10", "gray90"), command=self.cancel_or_close)
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_run = ctk.CTkButton(btn_row, text=t("subtitle_gui.generate_btn"), height=45, font=ctk.CTkFont(size=14, weight="bold"), fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER, command=self.start_generation)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 0))
        
        self.status_label = ctk.CTkLabel(self.main_frame, text=t("common.ready"), anchor="w", font=ctk.CTkFont(size=11), text_color="gray")
        self.status_label.pack(side="bottom", pady=(0, 5))

    def create_compact_setting(self, parent, label, values, default, var_name):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(frame, text=label, width=70, anchor="w", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left")
        var = ctk.StringVar(value=default)
        setattr(self, f"{var_name}_var", var)
        combo = ctk.CTkComboBox(frame, variable=var, values=values, height=24, font=("", 12),
                                fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER)
        combo.pack(side="left", fill="x", expand=True)
        setattr(self, f"{var_name}_combo", combo)

    def browse_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.out_dir_var.set(path)

    def toggle_log(self):
        if self.log_visible:
            self.log_frame.pack_forget()
            self.btn_toggle_log.configure(text=t("subtitle_gui.show_log") + " ▼")
            self.log_visible = False
        else:
            self.log_frame.pack(fill="both", padx=15, pady=5)
            self.btn_toggle_log.configure(text=t("subtitle_gui.hide_log") + " ▲")
            self.log_visible = True
        
        self.adjust_window_size()



    def cancel_or_close(self):
        """Cancel processing if running, otherwise close window."""
        if self.btn_run.cget("state") == "disabled":
            self.cancel_flag = True
            self.status_label.configure(text=t("subtitle_gui.cancelling"))
            # Terminate running subprocess if exists
            if self.current_process:
                from utils.ai_runner import kill_process_tree
                kill_process_tree(self.current_process)
                self.current_process = None
        else:
            self.on_closing()

    def on_closing(self):
        if self.current_process:
            from utils.ai_runner import kill_process_tree
            kill_process_tree(self.current_process)
        self.destroy()
        
    def start_generation(self):
        if not self.files:
            messagebox.showwarning(t("subtitle_gui.no_files_title"), t("subtitle_gui.no_files_body"))
            return
            
        # Check formats
        formats = []
        if self.fmt_srt.get(): formats.append("srt")
        if self.fmt_vtt.get(): formats.append("vtt")
        if self.fmt_txt.get(): formats.append("txt")
        if self.fmt_json.get(): formats.append("json")
        
        if not formats:
            messagebox.showwarning(t("subtitle_gui.no_format_title"), t("subtitle_gui.no_format_body"))
            return
        
        # CRITICAL: Reset cancel flag before each run
        self.cancel_flag = False
        self.current_process = None
            
        self.btn_run.configure(state="disabled", text=t("common.processing"))
        self.btn_cancel.configure(text=t("common.cancel"), fg_color=THEME_BTN_DANGER, hover_color=THEME_BTN_DANGER_HOVER, text_color="white")
        self.progress_bar.set(0)
        self.status_label.configure(text=t("ai_common.initializing"))
        self.log_area.delete("1.0", "end")
        
        threading.Thread(target=self.run_batch, args=(formats,), daemon=True).start()
        
    def run_batch(self, formats):
        script_path = src_dir / "scripts" / "ai_standalone" / "subtitle_gen.py"
        total = len(self.files)
        
        model = self.model_var.get().split(" ")[0]
        task = self.task_var.get()
        device = self.device_var.get()
        lang = self.lang_var.get()
        out_dir = self.out_dir_var.get().strip()
        
        fmt_str = ",".join(formats)
        
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        for i, file_path in enumerate(self.files, 1):
            # Check cancel flag before each file
            if self.cancel_flag:
                self.update_log("\n⚠️ Cancelled by user.\n")
                break
                
            self.update_status(f"Processing {i}/{total}: {file_path.name}...", (i-1)/total)
            self.update_log(f"--- Processing {i}/{total}: {file_path.name} ---\n")
            
            cmd = [sys.executable, str(script_path), str(file_path)]
            cmd.extend(["--model", model, "--task", task, "--device", device, "--format", fmt_str])
            if lang != "Auto": cmd.extend(["--lang", lang])
            if out_dir: cmd.extend(["--output_dir", out_dir])
            
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000, env=env)
                self.current_process = process  # Track for cancellation
                
                gpu_error_detected = False
                
                while True:
                    # Check cancel flag during processing
                    if self.cancel_flag:
                        try:
                            process.terminate()
                        except:
                            pass
                        break
                        
                    line = process.stdout.readline()
                    if not line and process.poll() is not None: break
                    if line: 
                        self.update_log(line)
                        # Check for GPU memory errors
                        if "CUDA out of memory" in line or "cuda malloc failed" in line.lower() or "gpu memory" in line.lower():
                            gpu_error_detected = True
                
                self.current_process = None
                        
                if not self.cancel_flag and process.returncode != 0:
                    if gpu_error_detected:
                        self.update_log(f"\n⚠️ GPU 메모리 부족! CPU 모드 권장: Device를 'cpu'로 변경하세요.\n")
                        self.after(0, lambda: self.device_var.set("cpu"))  # Auto-switch to CPU
                    self.update_log(f"Error: {file_path.name}\n")
            except Exception as e:
                self.update_log(f"Exception: {e}\n")
            
            if not self.cancel_flag:
                self.update_status(f"Finished {i}/{total}", i/total)
            
        self.after(0, self.finish_batch)
        
    def update_status(self, text, progress):
        self.after(0, lambda: self.status_label.configure(text=text))
        self.after(0, lambda: self.progress_bar.set(progress))
        
    def update_log(self, text):
        self.after(0, lambda: self.log_area.insert("end", text))
        self.after(0, lambda: self.log_area.see("end"))
        
    def download_models(self):
        """Download selected whisper model."""
        model_name = self.model_var.get()
        self.model_mgr.lbl_status.configure(text=f"Downloading {model_name}...", text_color="#E67E22")
        self.model_mgr.btn_action.configure(state="disabled")

        def _dl():
            try:
                engine_dir = Path(__file__).resolve().parent.parent
                if str(engine_dir) not in sys.path:
                    sys.path.append(str(engine_dir))

                from setup.download_models import download_whisper
                success = download_whisper(model_name)

                if success:
                    self.update_log(f"\nOK Whisper {model_name} model ready.\n")
                else:
                    self.update_log(f"\nOK Whisper {model_name} download failed.\n")
            except Exception as e:
                self.update_log(f"\nOK Error: {e}\n")

            self.after(0, lambda: self.model_mgr.check_status())
            self.after(0, lambda: self.model_mgr.btn_action.configure(state="normal"))

        threading.Thread(target=_dl, daemon=True).start()

    def _has_whisper_cache(self):
        try:
            from utils import paths
            if paths.WHISPER_DIR.exists() and any(paths.WHISPER_DIR.rglob("*")):
                return True
            hub = paths.RESOURCES_DIR / "cache" / "hf" / "hub"
            if hub.exists() and any(hub.rglob("models--Systran--faster-whisper-*")):
                return True
            return False
        except Exception:
            return False


    def finish_batch(self):
        self.btn_run.configure(state="normal", text=t("subtitle_gui.generate_btn"))
        self.btn_cancel.configure(text=t("common.cancel"), fg_color="transparent", hover_color="gray25", text_color="gray", border_color=THEME_BORDER)
        
        if self.cancel_flag:
            self.status_label.configure(text=t("common.cancelled"))
            messagebox.showinfo(t("common.cancelled"), t("subtitle_gui.cancelled_body"))
        else:
            self.status_label.configure(text=t("subtitle_gui.batch_complete"))
            self.progress_bar.set(1)
            messagebox.showinfo(t("common.complete"), t("subtitle_gui.complete_body"))

def generate_subtitles(target_path: str):
    """
    Open Subtitle Generation dialog.
    """
    app = SubtitleGUI(target_path)
    app.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        anchor = sys.argv[1]
        
        # Mutex - ensure only one GUI window opens
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("whisper_subtitle", anchor, timeout=0.2) is None:
            sys.exit(0)
        
        generate_subtitles(anchor)
    else:
        generate_subtitles(None)
