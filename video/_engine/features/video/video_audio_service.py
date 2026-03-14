import os
import subprocess
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Dict, Any

from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path
from .video_audio_state import VideoAudioState

class VideoAudioService:
    def __init__(self, state: VideoAudioState, on_update: Callable = None):
        self.state = state
        self.on_update = on_update
        self.state.ffmpeg_path = get_ffmpeg()

    def start_processing(self):
        if self.state.is_processing: return
        self.state.is_processing = True
        self.state.cancel_flag = False
        self.state.completed_count = 0
        self.state.total_count = len(self.state.files)
        self.state.progress_value = 0.0
        
        if self.on_update: self.on_update()
        threading.Thread(target=self._process_parallel, daemon=True).start()

    def cancel_processing(self):
        self.state.cancel_flag = True
        self.state.status_text = "Cancelling..."
        if self.on_update: self.on_update()

    def _process_parallel(self):
        jobs = self._prepare_jobs()
        total = len(jobs)
        success = 0
        errors = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self._run_single_job, job) for job in jobs]
            
            for future in as_completed(futures):
                if self.state.cancel_flag: break
                
                result = future.result()
                self.state.completed_count += 1
                self.state.progress_value = self.state.completed_count / (total if total > 0 else 1)
                
                if result['ok']: success += 1
                else: errors.append(result['error'])
                
                self.state.status_text = f"Processed {self.state.completed_count}/{total}"
                if self.on_update: self.on_update()

        self.state.is_processing = False
        if self.state.cancel_flag:
            self.state.status_text = "Cancelled"
        else:
            self.state.status_text = f"Complete: {success}/{total} successful"
        
        if self.on_update: self.on_update(finished=True, success=success, total=total, errors=errors)

    def _prepare_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        ffmpeg = self.state.ffmpeg_path
        mode = self.state.mode
        save_new_folder = self.state.save_to_folder

        for file in self.state.files:
            out_dir = file.parent
            if save_new_folder:
                out_dir = file.parent / "Audio_Output"
                out_dir.mkdir(exist_ok=True, parents=True)
            
            job = {'src': file, 'out_dir': out_dir, 'mode': mode}
            
            if mode == "extract":
                ext = self.state.extract_format.lower()
                out_file = out_dir / f"{file.stem}.{ext}"
                # wav uses -acodec copy, mp3 uses -acodec libmp3lame
                job['cmd'] = [ffmpeg, "-i", str(file), "-vn", "-acodec", "copy" if ext == "wav" else "libmp3lame", str(out_file), "-y"]
            elif mode == "remove":
                out_file = out_dir / f"{file.stem}_no_audio{file.suffix}"
                job['cmd'] = [ffmpeg, "-i", str(file), "-an", "-vcodec", "copy", str(out_file), "-y"]
            elif mode == "separate":
                if self.state.separate_mode == "Voice":
                    out_file = out_dir / f"{file.stem}_voice.wav"
                    job['cmd'] = [ffmpeg, "-i", str(file), "-af", "bandpass=f=1850:width_type=h:width=3100", str(out_file), "-y"]
                else:
                    out_file = out_dir / f"{file.stem}_bgm.wav"
                    job['cmd'] = [ffmpeg, "-i", str(file), "-af", "bandreject=f=1850:width_type=h:width=3100", str(out_file), "-y"]
            
            jobs.append(job)
        return jobs

    def _run_single_job(self, job):
        if self.state.cancel_flag: return {'ok': False, 'error': 'Cancelled'}
        try:
            subprocess.run(job['cmd'], check=True, capture_output=True)
            return {'ok': True}
        except subprocess.CalledProcessError as e:
            return {'ok': False, 'error': f"{job['src'].name}: {e.stderr.decode() if e.stderr else str(e)}"}
        except Exception as e:
            return {'ok': False, 'error': f"{job['src'].name}: {str(e)}"}
