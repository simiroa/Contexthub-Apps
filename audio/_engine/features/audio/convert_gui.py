import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import sys
import os
import subprocess
import threading

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/audio -> src
sys.path.append(str(src_dir))

from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path
from utils.explorer import get_selection_from_explorer
from utils.gui_lib import BaseWindow, FileListFrame, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_BTN_DANGER, THEME_BTN_DANGER_HOVER, THEME_TEXT_DIM, THEME_BORDER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from utils.i18n import t
from utils.audio_player import AudioPlayer

def _is_headless():
    return os.environ.get("CTX_HEADLESS") == "1" or os.environ.get("CTX_CAPTURE_MODE") == "1"

class AudioConvertGUI(BaseWindow):
    def __init__(self, target_path, demo=False):
        super().__init__(title="ContextUp Audio Converter", width=450, height=600, icon_name="audio_convert_format")
        
        self.demo_mode = demo or _is_headless()
        self.target_path = target_path
        
        if self.demo_mode:
            self.selection = []
            self.files = [Path("demo_audio.wav")]
        else:
            if isinstance(target_path, (list, tuple)):
                self.selection = [str(p) for p in target_path]
            else:
                # Fallback to Explorer COM if needed, but menu.py should have passed selection
                self.selection = get_selection_from_explorer(target_path)
                if not self.selection:
                    self.selection = [target_path]
                
            # Filter audio files
            audio_exts = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma', '.aiff'}
            self.files = [Path(p) for p in self.selection if Path(p).suffix.lower() in audio_exts]
            
            if not self.files:
                messagebox.showerror(t("common.error"), t("audio_convert_gui.no_audio_selected"))
                self.destroy()
                return

        self.var_new_folder = ctk.BooleanVar(value=True) # Default ON
        self.cancel_flag = False  # Cancel pattern for FFmpeg encoding
        self.current_process = None  # Track running FFmpeg process
        self.player = AudioPlayer()
        self.last_converted = None
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)


    def create_widgets(self):
        # 1. Header
        self.add_header(t("audio_convert_gui.title") + f" ({len(self.files)})", font_size=20)
        
        # 2. File List
        from utils.gui_lib import FileListFrame
        self.file_scroll = FileListFrame(self.main_frame, self.files, height=180)
        self.file_scroll.pack(fill="x", padx=20, pady=(0, 10))
        
        # 3. Parameters (2-Column Grid)
        param_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        param_frame.pack(fill="x", padx=20, pady=5)
        param_frame.grid_columnconfigure(0, weight=1)
        param_frame.grid_columnconfigure(1, weight=1)
        
        # Left Column: Format
        left_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(left_frame, text=t("audio_convert_gui.format_label"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        
        self.fmt_var = ctk.StringVar(value="MP3")
        self.fmt_combo = ctk.CTkComboBox(left_frame, variable=self.fmt_var, values=["MP3", "WAV", "OGG", "FLAC", "M4A"])
        self.fmt_combo.pack(fill="x", pady=(0, 5))
        
        self.var_meta = ctk.BooleanVar(value=True)
        self.chk_meta = ctk.CTkCheckBox(left_frame, text=t("audio_convert_gui.copy_metadata"), variable=self.var_meta)
        self.chk_meta.pack(anchor="w", pady=(10, 0))
        
        # Right Column: Quality
        right_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(right_frame, text=t("audio_convert_gui.quality_label"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        
        self.qual_var = ctk.StringVar(value="High")
        self.qual_combo = ctk.CTkComboBox(right_frame, variable=self.qual_var, values=["High", "Medium", "Low"])
        self.qual_combo.pack(fill="x", pady=(0, 5))

        # 4. Footer
        footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer_frame.pack(fill="x", padx=20, pady=20)
        
        self.progress = ctk.CTkProgressBar(footer_frame, height=10)
        self.progress.pack(fill="x", pady=(0, 15))
        self.progress.set(0)
        
        # Options
        opt_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        opt_row.pack(fill="x", pady=(0, 15))
        
        self.var_new_folder = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_row, text=t("audio_convert_gui.save_to_folder"), variable=self.var_new_folder).pack(side="left", padx=(0, 20))
        self.var_delete_org = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_row, text=t("image_convert_gui.delete_original"), variable=self.var_delete_org, 
                        text_color=THEME_BTN_DANGER_HOVER).pack(side="left")

        # Buttons
        btn_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_row.pack(fill="x")
        
        self.btn_cancel = ctk.CTkButton(btn_row, text=t("common.cancel"), height=45, fg_color="transparent", 
                                        border_width=1, border_color=THEME_BORDER, text_color=THEME_TEXT_DIM, command=self.cancel_or_close)
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_convert = ctk.CTkButton(btn_row, text=t("audio_convert_gui.convert"), height=45, 
                                         font=ctk.CTkFont(size=14, weight="bold"), command=self.start_convert)
        self.btn_convert.pack(side="left", fill="x", expand=True, padx=(0, 0))
        
        self.lbl_status = ctk.CTkLabel(self.main_frame, text=t("common.ready"), text_color=THEME_TEXT_DIM, font=("", 11))
        self.lbl_status.pack(pady=(0, 5))
        
        self.btn_play = ctk.CTkButton(self.main_frame, text="▶ Play Last Result", font=ctk.CTkFont(size=12), 
                                      fg_color="#1E8449", hover_color="#145A32", command=self.play_last)
        self.btn_play.pack(pady=(0, 10))
        self.btn_play.pack_forget()

    def cancel_or_close(self):
        """Cancel processing if running, otherwise close window."""
        if self.btn_convert.cget("state") == "disabled":
            self.cancel_flag = True
            self.lbl_status.configure(text=t("common.cancelling"))
            # Terminate running FFmpeg process if exists
            if self.current_process and self.current_process.poll() is None:
                try:
                    self.current_process.terminate()
                except:
                    pass
        else:
            self.destroy()

    def start_convert(self):
        # CRITICAL: Reset cancel flag before each run
        self.cancel_flag = False
        self.current_process = None
        
        self.btn_convert.configure(state="disabled", text=t("audio_convert_gui.converting"))
        self.btn_cancel.configure(fg_color=THEME_BTN_DANGER, hover_color=THEME_BTN_DANGER_HOVER, text_color="white")
        threading.Thread(target=self.run_conversion, daemon=True).start()

    def run_conversion(self):
        ffmpeg = get_ffmpeg()
        fmt = self.fmt_var.get().lower()
        copy_meta = self.var_meta.get()
        quality = self.qual_var.get()
        
        total = len(self.files)
        success = 0
        errors = []
        
        for i, path in enumerate(self.files):
            # Check cancel flag before each file
            if self.cancel_flag:
                break
                
            self.lbl_status.configure(text=f"Processing {i+1}/{total}: {path.name}")
            self.progress.set(i / total)
            
            try:
                # Determine output directory
                if self.var_new_folder.get():
                    base_dir = path.parent / "Converted_Audio"
                    safe_dir = base_dir if not base_dir.exists() else get_safe_path(base_dir)
                    safe_dir.mkdir(exist_ok=True)
                    out_dir = safe_dir
                    out_name = f"{path.stem}.{fmt}"
                else:
                    out_dir = path.parent
                    out_name = f"{path.stem}_conv.{fmt}"
                
                output_path = get_safe_path(out_dir / out_name)
                
                cmd = [ffmpeg, "-i", str(path)]
                
                # Codec & Quality
                if fmt == "mp3":
                    cmd.extend(["-acodec", "libmp3lame"])
                    if quality == "High": cmd.extend(["-q:a", "0"]) # VBR best
                    elif quality == "Medium": cmd.extend(["-q:a", "4"])
                    else: cmd.extend(["-q:a", "6"])
                elif fmt == "wav":
                    cmd.extend(["-acodec", "pcm_s16le"])
                elif fmt == "ogg":
                    cmd.extend(["-acodec", "libvorbis"])
                    if quality == "High": cmd.extend(["-q:a", "6"])
                    elif quality == "Medium": cmd.extend(["-q:a", "4"])
                    else: cmd.extend(["-q:a", "2"])
                elif fmt == "flac":
                    cmd.extend(["-acodec", "flac"])
                elif fmt == "m4a":
                    cmd.extend(["-acodec", "aac"])
                    if quality == "High": cmd.extend(["-b:a", "256k"])
                    elif quality == "Medium": cmd.extend(["-b:a", "192k"])
                    else: cmd.extend(["-b:a", "128k"])
                
                # Metadata
                if not copy_meta:
                    cmd.extend(["-map_metadata", "-1"])
                
                cmd.extend(["-y", str(output_path)])
                
                # Check cancel before running FFmpeg
                if self.cancel_flag:
                    break
                
                self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.current_process.wait()
                
                if self.cancel_flag:
                    break
                    
                if self.current_process.returncode != 0:
                    _, stderr = self.current_process.communicate()
                    raise Exception(f"FFmpeg error: {stderr.decode() if stderr else 'Unknown'}")
                
                self.current_process = None
                success += 1
                self.last_converted = output_path
                
                # Handle Deletion
                if self.var_delete_org.get() and path.exists():
                    try:
                        import os
                        os.remove(path)
                    except Exception as e:
                        errors.append(f"Delete failed: {path.name} ({str(e)})")
                
            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")
                
        self.progress.set(1.0)
        self.btn_convert.configure(state="normal", text=t("audio_convert_gui.convert"))
        self.btn_cancel.configure(fg_color="transparent", hover_color="gray25", text_color=THEME_TEXT_DIM)
        
        if self.cancel_flag:
            self.lbl_status.configure(text=t("common.cancelled"))
            messagebox.showinfo(t("common.cancelled"), t("audio_convert_gui.conversion_cancelled"))
        else:
            self.lbl_status.configure(text=t("common.complete"))
            
            msg = f"Converted {success}/{total} files."
            if errors:
                msg += "\n\n" + t("common.errors") + ":\n" + "\n".join(errors[:5])
                messagebox.showwarning(t("dialogs.operation_complete"), msg)
            else:
                if self.last_converted:
                    self.btn_play.pack(pady=(0, 10))
                messagebox.showinfo(t("common.success"), msg)
                # self.destroy() # Don't destroy immediately so user can play

    def play_last(self):
        if self.last_converted:
            self.player.play(self.last_converted)

    def on_closing(self):
        self.player.stop()
        self.destroy()

def run_gui(target_path):
    app = AudioConvertGUI(target_path)
    app.mainloop()

if __name__ == "__main__":
    # Demo mode for screenshots
    if "--demo" in sys.argv or _is_headless():
        app = AudioConvertGUI(None, demo=True)
        app.mainloop()
    elif len(sys.argv) > 1:
        anchor = sys.argv[1]
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("audio_convert", anchor, timeout=0.2) is None:
            sys.exit(0)

        # Use all command line arguments
        paths = [Path(p) for p in sys.argv[1:] if Path(p).exists()]
        run_gui(paths if len(paths) > 1 else paths[0])
    else:
        # Debug
        run_gui(str(Path.home() / "Music"))
