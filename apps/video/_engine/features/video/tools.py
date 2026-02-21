import os
import subprocess
from pathlib import Path
from tkinter import messagebox


from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path

def extract_audio(target_path: str, selection=None):
    from . import audio_gui
    audio_gui.run_gui(selection if selection else target_path)

def remove_audio(target_path: str, selection=None):
    from . import audio_gui
    audio_gui.run_gui(selection if selection else target_path)

def convert_video(target_path: str, selection=None):
    from . import convert_gui
    convert_gui.run_gui(target_path, selection=selection)

def create_proxy(target_path: str, selection=None):
    # Proxy is just a preset in convert_video now
    from . import convert_gui
    convert_gui.run_gui(target_path, selection=selection)

def seq_to_video(target_path: str):
    from features.sequence import to_video_gui
    to_video_gui.run_gui(target_path)

def frame_interp_30fps(target_path: str):
    """
    Interpolate video to 30fps using FFmpeg minterpolate filter.
    Now with progress display and cancel capability.
    """
    import threading
    import re
    import customtkinter as ctk
    
    path = Path(target_path)
    ffmpeg = get_ffmpeg()
    
    if not ffmpeg:
        messagebox.showerror("Error", "FFmpeg not found. Please install FFmpeg.")
        return
    
    # Get video duration first
    try:
        probe_cmd = [ffmpeg, "-i", str(path)]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, errors='ignore')
        
        duration_seconds = 0
        # Parse duration from ffmpeg output (format: Duration: HH:MM:SS.MS)
        duration_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+)\.(\d+)', result.stderr)
        if duration_match:
            h, m, s, ms = map(int, duration_match.groups())
            duration_seconds = h * 3600 + m * 60 + s + ms / 100
    except:
        duration_seconds = 0
    
    output_path = get_safe_path(path.with_name(f"{path.stem}_30fps.mp4"))
    
    # Create progress window
    class ProgressWindow(ctk.CTkToplevel):
        def __init__(self, master):
            super().__init__(master)
            self.title("Video Processing")
            self.geometry("500x450")
            self.resizable(False, False)
            
            # Center on screen
            self.update_idletasks()
            x = (self.winfo_screenwidth() - 450) // 2
            y = (self.winfo_screenheight() - 180) // 2
            self.geometry(f"+{x}+{y}")
            
            self.cancelled = False
            self.process = None
            self.finished = False
            
            # Title
            ctk.CTkLabel(self, text=f"Processing: {path.name}", font=("", 14, "bold")).pack(pady=(15, 5))
            ctk.CTkLabel(self, text="Interpolating to 30fps (this may take a while)", text_color="gray").pack()
            
            # Progress bar
            self.progress = ctk.CTkProgressBar(self, width=380)
            self.progress.pack(pady=15)
            self.progress.set(0)
            
            # Status
            self.status_label = ctk.CTkLabel(self, text="Starting...", text_color="gray")
            self.status_label.pack()
            
            # Cancel button
            self.cancel_btn = ctk.CTkButton(self, text="Cancel", fg_color="#E74C3C", hover_color="#C0392B",
                                            command=self.cancel)
            self.cancel_btn.pack(pady=10)
            
            self.protocol("WM_DELETE_WINDOW", self.cancel)
            
        def cancel(self):
            self.cancelled = True
            if self.process:
                try:
                    self.process.terminate()
                except:
                    pass
            self.finished = True
            self.destroy()
            
        def update_progress(self, progress, status):
            if not self.winfo_exists():
                return
            try:
                self.progress.set(progress)
                self.status_label.configure(text=status)
            except:
                pass
            
        def finish(self, success, message):
            if self.finished:
                return
            self.finished = True
            try:
                self.destroy()
            except:
                pass
            if success:
                messagebox.showinfo("Success", message)
            else:
                if not self.cancelled:
                    messagebox.showerror("Error", message)
    
    # Create and show progress window
    try:
        root = ctk.CTk()
        root.withdraw()
        
        progress_win = ProgressWindow(root)
        progress_win.attributes("-topmost", True)
        progress_win.lift()
        
        def run_ffmpeg():
            cmd = [
                ffmpeg, "-i", str(path),
                "-filter:v", "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
                "-c:v", "libx264", "-crf", "20",
                "-c:a", "copy",
                "-progress", "pipe:1",
                "-y", str(output_path)
            ]
            
            try:
                progress_win.process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    errors='ignore'
                )
                
                current_time = 0
                while True:
                    if progress_win.cancelled:
                        break
                        
                    line = progress_win.process.stdout.readline()
                    if not line and progress_win.process.poll() is not None:
                        break
                    
                    # Parse FFmpeg progress output
                    if line.startswith("out_time_ms="):
                        try:
                            time_ms = int(line.split("=")[1].strip())
                            current_time = time_ms / 1000000  # Convert to seconds
                            if duration_seconds > 0:
                                progress = min(current_time / duration_seconds, 1.0)
                                status = f"{int(progress * 100)}% - {int(current_time)}s / {int(duration_seconds)}s"
                                progress_win.after(0, lambda p=progress, s=status: progress_win.update_progress(p, s))
                        except:
                            pass
                
                _, stderr = progress_win.process.communicate()
                
                if progress_win.cancelled:
                    # Clean up partial file
                    try:
                        if output_path.exists():
                            output_path.unlink()
                    except:
                        pass
                    root.after(0, root.destroy)
                    return
                
                if progress_win.process.returncode == 0:
                    progress_win.after(0, lambda: progress_win.finish(True, f"Created {output_path.name}"))
                else:
                    progress_win.after(0, lambda: progress_win.finish(False, f"FFmpeg failed:\n{stderr[:500]}"))
                    
            except Exception as e:
                progress_win.after(0, lambda: progress_win.finish(False, f"Failed: {e}"))
            finally:
                root.after(100, root.destroy)
        
        # Start processing in background
        threading.Thread(target=run_ffmpeg, daemon=True).start()
        
        # Run the progress window
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed: {e}")
