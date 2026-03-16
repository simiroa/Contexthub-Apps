import os
import subprocess
import sys
from pathlib import Path
from typing import List, Callable, Optional
import threading

from utils.ai_runner import kill_process_tree

class AudioSeparateService:
    def __init__(self):
        self.current_process = None
        self.cancel_flag = False

    def separate_audio(
        self,
        input_paths: List[Path],
        model: str,
        output_format: str,
        mode: str,
        custom_output_dir: Optional[Path] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_complete: Optional[Callable[[int, int, List[str], Optional[Path]], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ):
        self.cancel_flag = False
        total = len(input_paths)
        success = 0
        errors = []
        last_output_dir = None
        
        python_exe = sys.executable

        for i, path in enumerate(input_paths):
            if self.cancel_flag:
                break

            if on_progress:
                on_progress(i, total, path.name)

            try:
                output_dir = custom_output_dir or (path.parent / "Separated_Audio")
                if not output_dir.exists():
                    output_dir.mkdir(parents=True, exist_ok=True)
                
                cmd = [python_exe, "-m", "demucs", "-n", model, "-o", str(output_dir), str(path)]
                
                if output_format == "mp3": 
                    cmd.append("--mp3")
                elif output_format == "flac": 
                    cmd.append("--flac")
                # default is wav
                
                if "2" in mode:
                    cmd.append("--two-stems=vocals")
                
                if on_log:
                    on_log(f"Running command: {' '.join(cmd)}")

                self.current_process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # We need to capture the output for logs
                for line in self.current_process.stdout:
                    if self.cancel_flag:
                        break
                    if on_log:
                        on_log(line.strip())
                
                self.current_process.wait()

                if self.cancel_flag:
                    break

                if self.current_process.returncode != 0:
                    raise Exception(f"Demucs error: Exit code {self.current_process.returncode}")

                success += 1
                last_output_dir = output_dir

            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")

        if on_complete:
            on_complete(success, total, errors, last_output_dir)

    def cancel(self):
        self.cancel_flag = True
        if self.current_process:
            kill_process_tree(self.current_process)
            self.current_process = None
