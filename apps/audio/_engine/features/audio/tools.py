import os
import subprocess
from pathlib import Path
from tkinter import messagebox

from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path


def convert_format(target_path: str):
    from features.audio import convert_gui
    convert_gui.run_gui(target_path)


def optimize_volume(target_path: str):
    try:
        path = Path(target_path)
        ffmpeg = get_ffmpeg()
        output_path = get_safe_path(path.with_name(f"{path.stem}_optimized{path.suffix}"))
        
        # Loudnorm
        cmd = [
            ffmpeg, "-i", str(path),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-y", str(output_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        messagebox.showinfo("Success", f"Optimized volume: {output_path.name}")
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed: {e}")


def extract_voice(target_path: str):
    # Use the unified VideoAudioGUI which handles audio files too
    from features.video import audio_gui
    audio_gui.run_gui(target_path)


def extract_bgm(target_path: str):
    # Use the unified VideoAudioGUI which handles audio files too
    from features.video import audio_gui
    audio_gui.run_gui(target_path)
