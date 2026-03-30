import os
import subprocess
from pathlib import Path
from typing import List, Callable, Optional

from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path

class AudioConvertService:
    def __init__(self):
        self.ffmpeg = get_ffmpeg()
        self.current_process = None
        self.cancel_flag = False

    def convert_audio(
        self,
        input_paths: List[Path],
        output_format: str,
        quality: str,
        copy_metadata: bool,
        save_to_new_folder: bool,
        custom_output_dir: Optional[Path],
        delete_original: bool,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_complete: Optional[Callable[[int, int, List[str], Optional[Path]], None]] = None
    ):
        self.cancel_flag = False
        total = len(input_paths)
        success = 0
        errors = []
        last_converted = None

        for i, path in enumerate(input_paths):
            if self.cancel_flag:
                break

            if on_progress:
                on_progress(i, total, path.name)

            try:
                # Output directory & name
                fmt = output_format.lower()
                if custom_output_dir:
                    out_dir = custom_output_dir
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_name = f"{path.stem}.{fmt}"
                elif save_to_new_folder:
                    base_dir = path.parent / "Converted_Audio"
                    if not base_dir.exists():
                        base_dir.mkdir(parents=True, exist_ok=True)
                    out_dir = base_dir
                    out_name = f"{path.stem}.{fmt}"
                else:
                    out_dir = path.parent
                    out_name = f"{path.stem}_conv.{fmt}"

                output_path = get_safe_path(out_dir / out_name)

                # FFmpeg Command
                cmd = [self.ffmpeg, "-i", str(path)]

                if fmt == "mp3":
                    cmd.extend(["-acodec", "libmp3lame"])
                    if quality == "High": cmd.extend(["-q:a", "0"])
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
                elif fmt == "aac":
                    cmd.extend(["-acodec", "aac"])
                    if quality == "High": cmd.extend(["-b:a", "256k"])
                    elif quality == "Medium": cmd.extend(["-b:a", "192k"])
                    else: cmd.extend(["-b:a", "128k"])

                if not copy_metadata:
                    cmd.extend(["-map_metadata", "-1"])

                cmd.extend(["-y", str(output_path)])

                if self.cancel_flag:
                    break

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
                last_converted = output_path

                if delete_original and path.exists():
                    try:
                        os.remove(path)
                    except Exception as e:
                        errors.append(f"Delete failed: {path.name} ({str(e)})")

            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")

        if on_complete:
            on_complete(success, total, errors, last_converted)

    def cancel(self):
        self.cancel_flag = True
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
            except:
                pass
