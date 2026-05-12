import json
import os
import subprocess
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Dict, Any

from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path
from .video_convert_state import VideoConvertState


_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _caps_cache_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "Contexthub" / "cache" / "ffmpeg_caps.json"


def _load_cached_nvenc(ffmpeg_path: str) -> bool | None:
    """Return cached has_nvenc for the given ffmpeg binary, or None if no valid cache."""
    if not ffmpeg_path:
        return None
    try:
        p = Path(ffmpeg_path)
        if not p.exists():
            return None
        mtime = p.stat().st_mtime_ns
        size = p.stat().st_size
        cache_file = _caps_cache_path()
        if not cache_file.exists():
            return None
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        entry = data.get(str(p.resolve()))
        if not entry:
            return None
        if entry.get("mtime_ns") == mtime and entry.get("size") == size:
            return bool(entry.get("has_nvenc", False))
    except Exception:
        return None
    return None


def _store_cached_nvenc(ffmpeg_path: str, has_nvenc: bool) -> None:
    try:
        p = Path(ffmpeg_path)
        if not p.exists():
            return
        cache_file = _caps_cache_path()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data[str(p.resolve())] = {
            "mtime_ns": p.stat().st_mtime_ns,
            "size": p.stat().st_size,
            "has_nvenc": bool(has_nvenc),
        }
        cache_file.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def _probe_nvenc(ffmpeg_path: str) -> bool:
    if not ffmpeg_path:
        return False
    try:
        res = subprocess.run(
            [ffmpeg_path, "-encoders"],
            capture_output=True,
            text=True,
            errors="ignore",
            creationflags=_CREATE_NO_WINDOW,
        )
        return "h264_nvenc" in res.stdout
    except Exception:
        return False


class VideoConvertService:
    def __init__(self, state: VideoConvertState, on_update: Callable = None):
        self.state = state
        self.on_update = on_update
        self.active_processes = []
        self.state.ffmpeg_path = get_ffmpeg()

        self._nvenc_ready = threading.Event()
        # Prefer cached capability so the UI can show the correct state immediately.
        cached = _load_cached_nvenc(self.state.ffmpeg_path)
        if cached is not None:
            self.state.has_nvenc = cached
            self._nvenc_ready.set()
        else:
            self.state.has_nvenc = False
            self._start_nvenc_probe()

    def _start_nvenc_probe(self) -> None:
        """Probe NVENC support in a background thread; notify UI when done."""
        def _run():
            try:
                has_nvenc = _probe_nvenc(self.state.ffmpeg_path)
                self.state.has_nvenc = has_nvenc
                _store_cached_nvenc(self.state.ffmpeg_path, has_nvenc)
            finally:
                self._nvenc_ready.set()
                if self.on_update:
                    try:
                        self.on_update()
                    except Exception:
                        pass
        threading.Thread(target=_run, daemon=True, name="nvenc-probe").start()

    def ensure_nvenc_checked(self, timeout: float = 5.0) -> bool:
        """Block until the NVENC probe finishes (used right before encoding)."""
        if not self._nvenc_ready.is_set():
            self._nvenc_ready.wait(timeout)
        return self.state.has_nvenc

    def check_nvenc(self) -> bool:
        """Kept for backwards compatibility; prefer state.has_nvenc."""
        return self.ensure_nvenc_checked()

    def add_inputs(self, paths: List[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            if path in self.state.files:
                continue
            self.state.files.append(path)
        if self.on_update:
            self.on_update()

    def remove_input_at(self, index: int) -> None:
        if 0 <= index < len(self.state.files):
            self.state.files.pop(index)
            if self.on_update:
                self.on_update()

    def clear_inputs(self) -> None:
        self.state.files.clear()
        if self.on_update:
            self.on_update()

    def start_conversion(self):
        if self.state.is_processing: return
        self.ensure_nvenc_checked()
        self.state.is_processing = True
        self.state.cancel_flag = False
        self.state.completed_count = 0
        self.state.total_count = len(self.state.files)
        self.state.progress_value = 0.0
        self.active_processes = []
        
        if self.on_update: self.on_update()
        threading.Thread(target=self._process_parallel, daemon=True).start()

    def cancel_conversion(self):
        self.state.cancel_flag = True
        for p in self.active_processes:
            if p.poll() is None:
                try: p.terminate()
                except: pass
        self.state.status_text = "Cancelling..."
        if self.on_update: self.on_update()

    def _process_parallel(self):
        jobs = self._prepare_jobs()
        total = len(jobs)
        success = 0
        errors = []
        
        # Limit to 3 threads for video encoding
        with ThreadPoolExecutor(max_workers=min(3, total if total > 0 else 1)) as executor:
            futures = [executor.submit(self._run_single_job, job) for job in jobs]
            
            for future in as_completed(futures):
                if self.state.cancel_flag: break
                
                result = future.result()
                self.state.completed_count += 1
                self.state.progress_value = self.state.completed_count / total
                
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
        out_dir_cache = {}
        ffmpeg = self.state.ffmpeg_path
        fmt = self.state.output_format
        scale = self.state.scale
        crf = self.state.crf
        save_new_folder = self.state.save_to_folder
        custom_output_dir = self.state.custom_output_dir
        delete_original = self.state.delete_original

        for path in self.state.files:
            suffix = path.suffix
            if "MP4" in fmt: suffix = ".mp4"
            elif "MOV" in fmt: suffix = ".mov"
            elif "MKV" in fmt: suffix = ".mkv"
            elif "GIF" in fmt: suffix = ".gif"

            if custom_output_dir:
                out_dir = custom_output_dir
                out_dir.mkdir(exist_ok=True, parents=True)
                out_name = f"{path.stem}{suffix}"
            elif save_new_folder:
                base_dir = path.parent / "Converted"
                if base_dir not in out_dir_cache:
                    safe_dir = get_safe_path(base_dir) if base_dir.exists() else base_dir
                    safe_dir.mkdir(exist_ok=True, parents=True)
                    out_dir_cache[base_dir] = safe_dir
                out_dir = out_dir_cache[base_dir]
                out_name = f"{path.stem}{suffix}"
            else:
                out_dir = path.parent
                out_name = f"{path.stem}_conv{suffix}"

            output_path = get_safe_path(out_dir / out_name)

            cmd = [ffmpeg, "-i", str(path)]
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
                        w = int(self.state.custom_width)
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
                        w = int(self.state.custom_width)
                        vf.append(f"scale={w}:-2")
                    except: pass
                if vf: cmd.extend(["-vf", ",".join(vf)])

            cmd.extend(["-y", str(output_path)])
            jobs.append({'src': path, 'cmd': cmd, 'delete': delete_original})
        return jobs

    def _run_single_job(self, job):
        if self.state.cancel_flag: return {'ok': False, 'error': 'Cancelled'}
        try:
            p = subprocess.Popen(job['cmd'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.active_processes.append(p)
            _, stderr = p.communicate()
            if p in self.active_processes: self.active_processes.remove(p)
            
            if p.returncode != 0:
                return {'ok': False, 'error': f"{job['src'].name}: {stderr.decode() if stderr else 'Unknown error'}"}
            
            if job['delete'] and job['src'].exists():
                try: os.remove(job['src'])
                except: pass
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': f"{job['src'].name}: {str(e)}"}
