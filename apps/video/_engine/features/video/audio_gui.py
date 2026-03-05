import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import sys
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/video -> src
sys.path.append(str(src_dir))

from utils.external_tools import get_ffmpeg
from utils.explorer import get_selection_from_explorer
from utils.gui_lib import BaseWindow, FileListFrame, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN

class VideoAudioGUI(BaseWindow):
    def __init__(self, target_path, selection=None):
        super().__init__(title="ContextUp Audio Tools", width=650, height=700, icon_name="video_audio_tools")
        
        self.target_path = target_path
        if isinstance(selection, (list, tuple)):
            self.selection = [str(p) for p in selection]
        else:
            self.selection = get_selection_from_explorer(target_path)
            if not self.selection: self.selection = [target_path]
        
        self.files = [Path(p) for p in self.selection if Path(p).exists()]
        
        self.var_new_folder = ctk.BooleanVar(value=True)
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # 1. Header & File List
        self.add_header(f"Selected Files ({len(self.files)})")
        
        self.file_scroll = FileListFrame(self.main_frame, self.files, height=120)
        self.file_scroll.pack(fill="x", padx=20, pady=5)

        # 2. Tabs (Compact)
        self.tab_view = ctk.CTkTabview(self.main_frame, fg_color=THEME_CARD, 
                                        segmented_button_selected_color=THEME_BTN_PRIMARY,
                                        segmented_button_selected_hover_color=THEME_BTN_HOVER,
                                        segmented_button_unselected_color=THEME_DROPDOWN_FG,
                                        segmented_button_unselected_hover_color=THEME_DROPDOWN_BTN,
                                        border_width=1, border_color=THEME_BORDER, height=180)
        self.tab_view.pack(fill="x", padx=20, pady=(10, 10))
        
        self.tab_extract = self.tab_view.add("Extract Audio")
        self.tab_remove = self.tab_view.add("Remove Audio")
        self.tab_separate = self.tab_view.add("Separate (Voice/BGM)")
        
        # --- Extract Tab ---
        ctk.CTkLabel(self.tab_extract, text="Select Output Format:", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 8))
        self.ext_fmt = ctk.StringVar(value="MP3")
        
        radio_frame = ctk.CTkFrame(self.tab_extract, fg_color="transparent")
        radio_frame.pack(pady=8)
        ctk.CTkRadioButton(radio_frame, text="MP3 (Compressed)", variable=self.ext_fmt, value="MP3").pack(side="left", padx=15)
        ctk.CTkRadioButton(radio_frame, text="WAV (Lossless)", variable=self.ext_fmt, value="WAV").pack(side="left", padx=15)

        # --- Remove Tab ---
        ctk.CTkLabel(self.tab_remove, text="Remove audio track from video files", text_color="gray").pack(pady=(30, 8))
        ctk.CTkLabel(self.tab_remove, text="Video codec will be copied (fast)", text_color="gray", font=("", 11)).pack(pady=5)

        # --- Separate Tab ---
        ctk.CTkLabel(self.tab_separate, text="Separate Voice and BGM", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 8))
        ctk.CTkLabel(self.tab_separate, text="Uses simple frequency filtering", text_color="gray", font=("", 11)).pack(pady=5)
        
        self.sep_mode = ctk.StringVar(value="Voice")
        sep_frame = ctk.CTkFrame(self.tab_separate, fg_color="transparent")
        sep_frame.pack(pady=15)
        ctk.CTkRadioButton(sep_frame, text="Extract Voice", variable=self.sep_mode, value="Voice").pack(side="left", padx=15)
        ctk.CTkRadioButton(sep_frame, text="Extract BGM", variable=self.sep_mode, value="BGM").pack(side="left", padx=15)

        # 3. Footer (Outside Tabs)
        footer = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(5, 15))
        
        # Options
        ctk.CTkCheckBox(footer, text="Save to new folder", variable=self.var_new_folder).pack(anchor="w", pady=(0, 10))
        
        # Progress
        self.progress = ctk.CTkProgressBar(footer, height=8)
        self.progress.pack(fill="x", pady=(0, 10))
        self.progress.set(0)
        
        # Dynamic Action Button
        btn_container = ctk.CTkFrame(footer, fg_color="transparent")
        btn_container.pack(fill="x")
        
        ctk.CTkButton(btn_container, text="Cancel", fg_color="transparent", 
                     border_width=1, border_color=THEME_BORDER, 
                     command=self.on_closing, width=100).pack(side="left", padx=(0, 10))
        
        self.btn_action = ctk.CTkButton(btn_container, text="Extract Audio", 
                                       command=self.run_current_action,
                                       height=40, font=ctk.CTkFont(size=14, weight="bold"))
        self.btn_action.pack(side="left", fill="x", expand=True)
        
        # Status
        self.lbl_status = ctk.CTkLabel(self.main_frame, text="Ready", text_color="gray")
        self.lbl_status.pack(pady=(5, 10))
        
        # Tab change handler
        self.tab_view.configure(command=self.on_tab_change)
    
    def on_tab_change(self):
        current_tab = self.tab_view.get()
        if current_tab == "Extract Audio":
            self.btn_action.configure(text="Extract Audio", fg_color=THEME_BTN_PRIMARY)
        elif current_tab == "Remove Audio":
            self.btn_action.configure(text="Remove Audio", fg_color="#C0392B")
        elif current_tab == "Separate (Voice/BGM)":
            self.btn_action.configure(text="Process Separation", fg_color=THEME_BTN_PRIMARY)
    
    def run_current_action(self):
        current_tab = self.tab_view.get()
        if current_tab == "Extract Audio":
            self.run_extract()
        elif current_tab == "Remove Audio":
            self.run_remove()
        elif current_tab == "Separate (Voice/BGM)":
            self.run_separate()

    def run_extract(self):
        self.start_thread("extract")

    def run_remove(self):
        self.start_thread("remove")

    def run_separate(self):
        self.start_thread("separate")

    def start_thread(self, mode):
        self.btn_action.configure(state="disabled")
        self.cancel_flag = False
        threading.Thread(target=lambda: self.process_parallel(mode), daemon=True).start()

    def process_parallel(self, mode):
        ffmpeg = get_ffmpeg()
        if not ffmpeg or not Path(ffmpeg).exists():
            messagebox.showerror("Error", "FFmpeg not found!")
            self.btn_action.configure(state="normal")
            return

        total = len(self.files)
        save_new_folder = self.var_new_folder.get()
        jobs = []
        
        # Prepare Jobs
        for file in self.files:
            out_dir = file.parent
            if save_new_folder:
                out_dir = file.parent / "Audio_Output"
                out_dir.mkdir(exist_ok=True)
            
            job = {'src': file, 'out_dir': out_dir, 'mode': mode}
            
            if mode == "extract":
                ext = self.ext_fmt.get().lower()
                out_file = out_dir / f"{file.stem}.{ext}"
                job['cmd'] = [ffmpeg, "-i", str(file), "-vn", "-acodec", "copy" if ext == "wav" else "libmp3lame", str(out_file), "-y"]
            elif mode == "remove":
                out_file = out_dir / f"{file.stem}_no_audio{file.suffix}"
                job['cmd'] = [ffmpeg, "-i", str(file), "-an", "-vcodec", "copy", str(out_file), "-y"]
            elif mode == "separate":
                # Only one command per job for simplicity, create separate jobs for Voice/BGM?
                # The UI has radio button for MODE.
                if self.sep_mode.get() == "Voice":
                    out_file = out_dir / f"{file.stem}_voice.wav"
                    job['cmd'] = [ffmpeg, "-i", str(file), "-af", "bandpass=f=1850:width_type=h:width=3100", str(out_file), "-y"]
                else:
                    out_file = out_dir / f"{file.stem}_bgm.wav"
                    job['cmd'] = [ffmpeg, "-i", str(file), "-af", "bandreject=f=1850:width_type=h:width=3100", str(out_file), "-y"]
            
            jobs.append(job)

        success = 0
        errors = []
        completed = 0
        
        # Audio ops are usually I/O bound or fast CPU, but 3 is safe limit
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self._run_job, job) for job in jobs]
            
            for future in as_completed(futures):
                if getattr(self, 'cancel_flag', False): break
                
                res = future.result()
                completed += 1
                if res['ok']: success += 1
                else: errors.append(res['error'])
                
                self.after(0, lambda v=completed/total: self.progress.set(v))
                self.after(0, lambda v=completed: self.lbl_status.configure(text=f"Processed {v}/{total}"))

        self.after(0, lambda: self._finish(success, errors))

    def _run_job(self, job):
        if getattr(self, 'cancel_flag', False): return {'ok': False}
        try:
            # We don't capture output unless error to save memory/speed
            subprocess.run(job['cmd'], check=True, capture_output=True)
            return {'ok': True}
        except subprocess.CalledProcessError as e:
            return {'ok': False, 'error': f"{job['src'].name}: {e.stderr.decode() if e.stderr else str(e)}"}
        except Exception as e:
            return {'ok': False, 'error': f"{job['src'].name}: {str(e)}"}

    def _finish(self, success, errors):
        self.progress.set(1.0)
        self.btn_action.configure(state="normal")
        self.lbl_status.configure(text="Complete")
        
        msg = f"Processed {success}/{len(self.files)} files."
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5: msg += "\n..."
            messagebox.showwarning("Done with Errors", msg)
        else:
            messagebox.showinfo("Done", msg)

    def on_closing(self):
        self.cancel_flag = True
        self.destroy()

def run_gui(target_path, selection=None):
    app = VideoAudioGUI(target_path, selection=selection)
    app.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        anchor = sys.argv[1]
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("video_audio_tools", anchor, timeout=0.2) is None:
            sys.exit(0)

        paths = [Path(p) for p in sys.argv[1:] if Path(p).exists()]
        if not paths: sys.exit(0)
        run_gui(paths[0], selection=paths)
