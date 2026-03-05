import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import sys
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/video -> src
sys.path.append(str(src_dir))

from utils.external_tools import get_ffmpeg
from utils.explorer import get_selection_from_explorer
from utils.files import get_safe_path
from utils.gui_lib import BaseWindow, FileListFrame, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_BTN_DANGER, THEME_BTN_DANGER_HOVER, THEME_TEXT_DIM, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from utils.i18n import t
from core.config import MenuConfig

def _is_headless():
    return os.environ.get("CTX_HEADLESS") == "1" or os.environ.get("CTX_CAPTURE_MODE") == "1"

class VideoConvertGUI(BaseWindow):
    def __init__(self, target_path, selection=None, demo=False):
        # Sync Name
        self.tool_name = t("video_convert_gui.title")
        try:
             config = MenuConfig()
             item = config.get_item_by_id("video_convert")
             if item: self.tool_name = item.get("name", self.tool_name)
        except: pass

        super().__init__(title=self.tool_name, width=600, height=660, icon_name="video_convert")
        
        self.demo_mode = demo or _is_headless()
        self.target_path = target_path
        
        if self.demo_mode:
            self.selection = []
            self.files = [Path("demo_video.mp4")]
        else:
            if isinstance(selection, (list, tuple)):
                self.selection = [str(p) for p in selection]
            else:
                self.selection = get_selection_from_explorer(target_path)
                if not self.selection:
                    self.selection = [target_path]
                
            # Filter video files
            video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
            self.files = [Path(p) for p in self.selection if Path(p).suffix.lower() in video_exts]
            
            if not self.files:
                messagebox.showerror(t("common.error"), t("video_convert_gui.no_video_selected"))
                self.destroy()
                return

        self.var_new_folder = ctk.BooleanVar(value=True) # Default ON
        self.cancel_flag = False  # Cancel flag
        self.active_processes = []  # Track running FFmpeg processes for bulk kill
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)


    def create_widgets(self):
        # 0. FFmpeg Check Banner
        if not self.check_ffmpeg_exists():
            self.show_ffmpeg_banner()

        # 1. Header
        self.add_header(f"{self.tool_name} ({len(self.files)})", font_size=20)
        
    def check_ffmpeg_exists(self):
        import shutil
        ffmpeg = get_ffmpeg()
        if os.path.isabs(ffmpeg) and os.path.exists(ffmpeg):
            return True
        if shutil.which(ffmpeg):
            return True
        return False

    def show_ffmpeg_banner(self):
        banner = ctk.CTkFrame(self.main_frame, fg_color="#E74C3C", corner_radius=6)
        banner.pack(fill="x", padx=20, pady=(10, 0))
        
        lbl = ctk.CTkLabel(banner, text="⚠️ FFmpeg Missing", text_color="white", font=ctk.CTkFont(weight="bold"))
        lbl.pack(side="left", padx=10, pady=8)
        
        lbl_desc = ctk.CTkLabel(banner, text="Required for video tools", text_color="white", font=ctk.CTkFont(size=11))
        lbl_desc.pack(side="left", padx=5)
        
        btn = ctk.CTkButton(banner, text="Download", fg_color="white", text_color="#E74C3C", hover_color="#f0f0f0",
                            height=28, width=80, command=self.download_ffmpeg)
        btn.pack(side="right", padx=10, pady=5)

    def download_ffmpeg(self):
        ctx_root = os.environ.get("CTX_ROOT")
        if not ctx_root:
            messagebox.showerror("Error", "CTX_ROOT environment variable missing.")
            return
            
        script_path = Path(ctx_root) / "setup_ffmpeg.ps1"
        if not script_path.exists():
            # Try looking relative if env var is weird
            script_path = Path(__file__).parent.parent.parent.parent.parent.parent / "setup_ffmpeg.ps1"
            if not script_path.exists():
                messagebox.showerror("Error", f"Setup script not found at {script_path}")
                return

        if messagebox.askyesno("Install FFmpeg", "Download and install FFmpeg? (Requires PowerShell)"):
            try:
                # Open separate console to run the script
                subprocess.Popen(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                messagebox.showinfo("Installing", "Installation started in background console.\nPlease restart this tool after completion.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start installer: {e}")
        
        # 2. File List
        from utils.gui_lib import FileListFrame
        self.file_scroll = FileListFrame(self.main_frame, self.files, height=180)
        self.file_scroll.pack(fill="x", padx=20, pady=(0, 10))
        
        # 3. Parameters (2-Column Grid)
        param_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        param_frame.pack(fill="x", padx=20, pady=5)
        param_frame.grid_columnconfigure(0, weight=1)
        param_frame.grid_columnconfigure(1, weight=1)
        
        # Left Column: Format & Scale
        left_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(left_frame, text=t("video_convert_gui.format_label"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        
        # Check for NVENC
        self.has_nvenc = self.check_nvenc()
        formats = []
        if self.has_nvenc:
            formats.append("MP4 (H.264 NVENC)")
            
        formats.extend([
            "MP4 (H.264 High)", 
            "MP4 (H.264 Low/Proxy)", 
            "MOV (ProRes 422)", 
            "MOV (ProRes 4444)", 
            "MOV (DNxHD)",
            "MKV (Copy Stream)",
            "GIF (High Quality)"
        ])
        
        self.fmt_var = ctk.StringVar(value=formats[0])
        self.fmt_combo = ctk.CTkComboBox(left_frame, variable=self.fmt_var, values=formats, command=self.on_fmt_change)
        self.fmt_combo.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(left_frame, text=t("video_convert_gui.scale_label"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.scale_var = ctk.StringVar(value="100%")
        self.scale_combo = ctk.CTkComboBox(left_frame, variable=self.scale_var, values=["100%", "50%", "25%", "Custom Width"], command=self.on_scale_change)
        self.scale_combo.pack(fill="x", pady=(0, 5))
        
        self.entry_width = ctk.CTkEntry(left_frame, placeholder_text=t("video_convert_gui.width_placeholder"))
        
        # Right Column: Quality
        right_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        self.lbl_crf = ctk.CTkLabel(right_frame, text=t("video_convert_gui.quality_crf"), font=ctk.CTkFont(weight="bold"))
        self.lbl_crf.pack(anchor="w", pady=(5, 2))
        
        range_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        range_frame.pack(fill="x")
        
        self.crf_var = tk.IntVar(value=23)
        self.slider_crf = ctk.CTkSlider(range_frame, from_=0, to=51, number_of_steps=51, variable=self.crf_var, command=self.update_crf_label)
        self.slider_crf.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.lbl_crf_val = ctk.CTkLabel(range_frame, text="23", width=30)
        self.lbl_crf_val.pack(side="right")
        
        ctk.CTkLabel(right_frame, text=t("video_convert_gui.quality_hint"), text_color=THEME_TEXT_DIM, font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(2, 0))

        # 4. Footer
        footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer_frame.pack(fill="x", padx=20, pady=(20, 5))
        
        self.progress = ctk.CTkProgressBar(footer_frame, height=10)
        self.progress.pack(fill="x", pady=(0, 15))
        self.progress.set(0)
        
        # Options
        opt_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        opt_row.pack(fill="x", pady=(0, 15))
        
        ctk.CTkCheckBox(opt_row, text=t("video_convert_gui.save_to_folder"), variable=self.var_new_folder).pack(side="left", padx=(0, 20))
        self.var_delete_org = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_row, text=t("image_convert_gui.delete_original"), variable=self.var_delete_org, 
                       text_color=THEME_BTN_DANGER_HOVER).pack(side="left")

        # Buttons
        btn_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_row.pack(fill="x")
        
        self.btn_cancel = ctk.CTkButton(btn_row, text=t("common.cancel"), height=45, fg_color="transparent", 
                                        border_width=1, border_color=THEME_BORDER, text_color=("gray10", "gray90"), command=self.cancel_or_close)
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_convert = ctk.CTkButton(btn_row, text=t("video_convert_gui.start_conversion"), height=45, 
                                        font=ctk.CTkFont(size=14, weight="bold"), 
                                        command=self.start_convert)
        self.btn_convert.pack(side="left", fill="x", expand=True, padx=(0, 0))
        
        self.lbl_status = ctk.CTkLabel(self.main_frame, text=t("video_convert_gui.ready_to_convert"), text_color=THEME_TEXT_DIM, font=("", 11))
        self.lbl_status.pack(pady=(0, 5))

    def update_crf_label(self, value):
        self.lbl_crf_val.configure(text=str(int(value)))

    def on_fmt_change(self, choice):
        if "H.264" in choice:
            self.slider_crf.configure(state="normal")
            if "High" in choice: self.crf_var.set(18)
            else: self.crf_var.set(28)
        else:
            self.slider_crf.configure(state="disabled")
        self.update_crf_label(self.crf_var.get())

    def on_scale_change(self, choice):
        if choice == "Custom Width":
            self.entry_width.pack(fill="x", pady=(0, 5))
            self.adjust_window_size()
        else:
            self.entry_width.pack_forget()
            self.adjust_window_size()

    def check_nvenc(self):
        """Check if NVIDIA NVENC encoder is available."""
        try:
            ffmpeg = get_ffmpeg()
            # Run ffmpeg -encoders and check for h264_nvenc
            res = subprocess.run([ffmpeg, "-encoders"], capture_output=True, text=True, errors="ignore")
            # Look for "V..... h264_nvenc"
            return "h264_nvenc" in res.stdout
        except:
            return False

    def cancel_or_close(self):
        """Cancel processing if running, otherwise close window."""
        if self.btn_convert.cget("state") == "disabled":
            self.cancel_flag = True
            self.lbl_status.configure(text=t("video_convert_gui.cancelling"))
            
            # Terminate all running FFmpeg processes
            for p in self.active_processes:
                if p.poll() is None:
                    try:
                        p.terminate()
                    except:
                        pass
        else:
            self.destroy()

    def start_convert(self):
        self.cancel_flag = False
        self.active_processes = []
        
        # Limit to 3 threads for Video encoding to prevent system freeze
        self.threads = 3
        
        self.btn_convert.configure(state="disabled", text=f"{t('video_convert_gui.converting')} (Max {self.threads})")
        self.btn_cancel.configure(fg_color=THEME_BTN_DANGER, hover_color=THEME_BTN_DANGER_HOVER, text_color="white")
        threading.Thread(target=self.process_parallel, daemon=True).start()

    def process_parallel(self):
        ffmpeg = get_ffmpeg()
        fmt = self.fmt_var.get()
        scale = self.scale_var.get()
        crf = int(self.crf_var.get())
        
        save_new_folder = self.var_new_folder.get()
        delete_original = self.var_delete_org.get()
        
        # Pre-calculate jobs
        jobs = []
        out_dir_cache = {}
        
        for path in self.files:
            # Output filename
            suffix = path.suffix
            if "MP4" in fmt: suffix = ".mp4"
            elif "MOV" in fmt: suffix = ".mov"
            elif "MKV" in fmt: suffix = ".mkv"
            elif "GIF" in fmt: suffix = ".gif"
            
            # Determine output directory
            if save_new_folder:
                base_dir = path.parent / "Converted"
                if base_dir not in out_dir_cache:
                    safe_dir = base_dir if not base_dir.exists() else get_safe_path(base_dir)
                    safe_dir.mkdir(exist_ok=True)
                    out_dir_cache[base_dir] = safe_dir
                out_dir = out_dir_cache[base_dir]
                out_name = f"{path.stem}{suffix}" 
            else:
                out_dir = path.parent
                out_name = f"{path.stem}_conv{suffix}"
            
            output_path = get_safe_path(out_dir / out_name)
            
            # Build Command
            cmd = [ffmpeg, "-i", str(path)]
            
            # Video Codec
            if "NVENC" in fmt:
                cmd.extend(["-c:v", "h264_nvenc", "-cq", str(crf), "-preset", "p6", "-c:a", "aac"])
            elif "H.264" in fmt:
                cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-c:a", "aac"])
                if "Low" in fmt: cmd.extend(["-preset", "fast"])
            elif "ProRes 422" in fmt:
                cmd.extend(["-c:v", "prores_ks", "-profile:v", "2", "-c:a", "pcm_s16le"])
            elif "ProRes 4444" in fmt:
                cmd.extend(["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-c:a", "pcm_s16le"])
            elif "DNxHD" in fmt:
                cmd.extend(["-c:v", "dnxhd", "-profile:v", "dnxhr_hq", "-c:a", "pcm_s16le"])
            elif "Copy" in fmt:
                cmd.extend(["-c", "copy"])
                
            elif "GIF" in fmt:
                scale_filter = ""
                if scale == "50%": scale_filter = ",scale=iw/2:-1"
                elif scale == "25%": scale_filter = ",scale=iw/4:-1"
                elif scale == "Custom Width":
                    try:
                        w = int(self.entry_width.get())
                        scale_filter = f",scale={w}:-1"
                    except: pass
                
                filter_str = f"fps=15{scale_filter}:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
                cmd.extend(["-vf", filter_str, "-c:v", "gif"])
            
            if "GIF" not in fmt:
                vf = []
                if scale == "50%": vf.append("scale=iw/2:-2")
                elif scale == "25%": vf.append("scale=iw/4:-2")
                elif scale == "Custom Width":
                    try:
                        w = int(self.entry_width.get())
                        vf.append(f"scale={w}:-2")
                    except: pass
                
                if vf: cmd.extend(["-vf", ",".join(vf)])
            
            cmd.extend(["-y", str(output_path)])
            
            jobs.append({
                'src': path,
                'cmd': cmd,
                'delete': delete_original
            })

        total = len(jobs)
        success = 0
        errors = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(self._run_single_job, job) for job in jobs]
            
            for future in as_completed(futures):
                if self.cancel_flag:
                    break
                    
                result = future.result()
                completed += 1
                
                if result['ok']:
                    success += 1
                else:
                    errors.append(result['error'])
                
                self.after(0, lambda v=completed/total: self.progress.set(v))
                if completed < total:
                    self.after(0, lambda v=completed: self.lbl_status.configure(text=f"Processed {v}/{total}"))

        self.after(0, lambda: self._finish(success, errors))
    
    def _run_single_job(self, job):
        if self.cancel_flag: return {'ok': False, 'error': 'Cancelled'}
        
        try:
            # Run without startupinfo for now to debug 0xC0000135
            p = subprocess.Popen(job['cmd'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Register process
            self.active_processes.append(p)
            
            _, stderr = p.communicate()
            
            if p in self.active_processes:
                self.active_processes.remove(p)
            
            if p.returncode != 0:
                return {'ok': False, 'error': f"{job['src'].name}: {stderr.decode() if stderr else 'Unknown error'}"}
            
            if job['delete'] and job['src'].exists():
                try:
                    import os
                    os.remove(job['src'])
                except Exception as e:
                    return {'ok': False, 'error': f"Delete failed: {job['src'].name}"}
                    
            return {'ok': True}
            
        except Exception as e:
            return {'ok': False, 'error': f"{job['src'].name}: {str(e)}"}

    def _finish(self, success, errors):
        self.progress.set(1.0)
        self.btn_convert.configure(state="normal", text=t("video_convert_gui.start_conversion"))
        self.btn_cancel.configure(fg_color="transparent", hover_color="gray25", text_color=THEME_TEXT_DIM)
        
        if self.cancel_flag:
            self.lbl_status.configure(text=t("common.cancelled"))
            messagebox.showinfo(t("common.cancelled"), t("video_convert_gui.conversion_cancelled"))
        else:
            self.lbl_status.configure(text=t("video_convert_gui.conversion_complete"))
            
            msg = f"Converted {success}/{len(self.files)} files."
            if errors:
                msg += "\n\n" + t("common.errors") + ":\n" + "\n".join(errors[:5])
                messagebox.showwarning(t("dialogs.operation_complete"), msg)
            else:
                messagebox.showinfo(t("common.success"), msg)
                self.destroy()

    # Legacy method removed
    def run_conversion(self): pass

    def on_closing(self):
        self.destroy()

def run_gui(target_path, selection=None):
    app = VideoConvertGUI(target_path, selection=selection)
    app.mainloop()

if __name__ == "__main__":
    # Demo mode for screenshots
    if "--demo" in sys.argv or _is_headless():
        app = VideoConvertGUI(None, demo=True)
        app.mainloop()
    elif len(sys.argv) > 1:
        anchor = sys.argv[1]
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("video_convert", anchor, timeout=0.2) is None:
            sys.exit(0)

        # Use all command line arguments
        paths = [Path(p) for p in sys.argv[1:] if Path(p).exists()]
        run_gui(paths[0] if paths else None, selection=paths)
    else:
        run_gui(str(Path.home() / "Videos"))

