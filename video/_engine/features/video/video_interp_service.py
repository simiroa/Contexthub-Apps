import os
import subprocess
from pathlib import Path
from typing import Callable, Optional

from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path

class VideoInterpService:
    def __init__(self):
        self.ffmpeg = get_ffmpeg()
        self.current_process = None
        self.cancel_flag = False

    def interpolate(
        self,
        input_path: Path,
        multiplier: str,
        quality_mode: str,
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_complete: Optional[Callable[[bool, Optional[Path], Optional[str]], None]] = None
    ):
        self.cancel_flag = False
        self.current_process = None

        try:
            # 1. Output setup
            out_dir = input_path.parent / "Interpolated"
            if not out_dir.exists():
                out_dir.mkdir(parents=True, exist_ok=True)
            
            output_name = f"{input_path.stem}_{multiplier}_{quality_mode}.mp4"
            output_path = get_safe_path(out_dir / output_name)

            if on_progress:
                on_progress(0.1, f"Analyzing {input_path.name}...")

            # 2. FFmpeg Command Building
            cmd = [self.ffmpeg, "-i", str(input_path)]
            
            # minterpolate filter
            # mi_mode: mci (high), blend (fast)
            # fps: target fps
            
            target_fps = "30"
            if multiplier == "2x":
                # Get current fps first? Let's assume common 24 or 30
                # Real implementation should detect fps via ffprobe
                # For simplicity, we use multiplier if possible or fixed target
                cmd.extend(["-filter:v", f"minterpolate=fps=60:mi_mode={quality_mode}"])
            elif multiplier == "4x":
                cmd.extend(["-filter:v", f"minterpolate=fps=120:mi_mode={quality_mode}"])
            elif "30fps" in multiplier:
                cmd.extend(["-filter:v", f"minterpolate=fps=30:mi_mode={quality_mode}"])
            elif "60fps" in multiplier:
                cmd.extend(["-filter:v", f"minterpolate=fps=60:mi_mode={quality_mode}"])

            cmd.extend(["-y", str(output_path)])

            if on_progress:
                on_progress(0.3, "Processing interpolation (This can be very slow)...")

            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.current_process.wait()

            if self.cancel_flag:
                if on_complete: on_complete(False, None, "Cancelled")
                return

            if self.current_process.returncode != 0:
                _, stderr = self.current_process.communicate()
                raise Exception(f"FFmpeg error: {stderr.decode() if stderr else 'Unknown'}")

            if on_complete:
                on_complete(True, output_path, None)

        except Exception as e:
            if on_complete:
                on_complete(False, None, str(e))

    def cancel(self):
        self.cancel_flag = True
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
            except:
                pass
