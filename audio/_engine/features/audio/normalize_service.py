import os
import subprocess
from pathlib import Path
from typing import List, Callable, Optional

from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path

class AudioNormalizeService:
    def __init__(self):
        self.ffmpeg = get_ffmpeg()
        self.current_process = None
        self.cancel_flag = False

    def normalize_audio(
        self,
        input_paths: List[Path],
        target_loudness: float = -16.0,
        true_peak: float = -1.5,
        loudness_range: float = 11.0,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_complete: Optional[Callable[[int, int, List[str], Optional[Path]], None]] = None
    ):
        self.cancel_flag = False
        total = len(input_paths)
        success = 0
        errors = []
        last_output_path = None

        for i, path in enumerate(input_paths):
            if self.cancel_flag:
                break

            if on_progress:
                on_progress(i, total, path.name)

            try:
                output_path = get_safe_path(path.with_name(f"{path.stem}_normalized{path.suffix}"))
                
                # loudnorm=I=-16:TP=-1.5:LRA=11
                af_val = f"loudnorm=I={target_loudness}:TP={true_peak}:LRA={loudness_range}"
                
                cmd = [
                    self.ffmpeg, "-i", str(path),
                    "-af", af_val,
                    "-y", str(output_path)
                ]

                self.current_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                self.current_process.wait()

                if self.cancel_flag:
                    break

                if self.current_process.returncode != 0:
                    _, stderr = self.current_process.communicate()
                    raise Exception(f"FFmpeg error: {stderr.decode() if stderr else 'Unknown'}")

                success += 1
                last_output_path = output_path

            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")

        if on_complete:
            on_complete(success, total, errors, last_output_path)

    def cancel(self):
        self.cancel_flag = True
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
            except:
                pass
