from __future__ import annotations

import base64
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from utils.i18n import t
from features.video.youtube_downloader_state import DownloadItem, YoutubeDownloaderState

# ── yt-dlp dependency gating ──
try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    yt_dlp = None
    HAS_YTDLP = False

# ── quality mapping ──
QUALITY_MAP = {
    "Best Video+Audio": "bestvideo+bestaudio/best",
    "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "Audio Only (MP3)": "__audio_mp3__",
    "Audio Only (M4A)": "__audio_m4a__",
}


class YoutubeDownloaderService:
    def __init__(self) -> None:
        self.state = YoutubeDownloaderState()
        self._history_lock = threading.Lock()
        self._load_initial_settings()
        self._workflow_names = list(QUALITY_MAP.keys())

    def _load_initial_settings(self) -> None:
        # Simplified settings loading for the service class
        self.state.output_options.output_dir = Path.home() / "Downloads"
        # We could load from settings.json if needed, but keeping it simple for now
        self.state.parameter_values["quality"] = "Best Video+Audio"
        self.state.parameter_values["subs"] = False

    def get_workflow_names(self) -> list[str]:
        return self._workflow_names

    def select_workflow(self, name: str) -> None:
        self.state.workflow_name = name
        self.state.parameter_values["quality"] = name

    def get_ui_definition(self) -> list[dict[str, Any]]:
        return [
            {
                "key": "quality",
                "label": t("youtube_downloader.format_label", "Format"),
                "type": "choice",
                "options": list(QUALITY_MAP.keys()),
                "default": "Best Video+Audio"
            },
            {
                "key": "subs",
                "label": t("youtube_downloader.subs", "Subtitles"),
                "type": "bool",
                "default": False
            }
        ]

    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value
        if key == "quality":
            self.state.workflow_name = value

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir)
        self.state.output_options.file_prefix = file_prefix.strip() or "yt_dl"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def analyze_url(self, url: str) -> dict:
        if not HAS_YTDLP:
            raise ImportError("yt-dlp is not installed.")

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "legacyserver_connect": True,
            "extractor_args": {"youtube": {"player_client": ["web", "android"]}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        self.state.video_info = info
        self.state.url = url
        return info

    def fetch_thumbnail_base64(self, url: str) -> Optional[str]:
        try:
            import urllib.request
            from io import BytesIO
            from PIL import Image

            with urllib.request.urlopen(url) as u:
                raw = u.read()
            img = Image.open(BytesIO(raw))
            img.thumbnail((160, 90))
            buf = BytesIO()
            img.save(buf, format="JPEG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            self.state.thumbnail_b64 = b64
            return b64
        except Exception:
            return None

    def add_to_queue(self) -> Optional[DownloadItem]:
        if not self.state.video_info:
            return None
        
        info = self.state.video_info
        item = DownloadItem(
            id=self.state.download_counter,
            title=info.get("title") or "Unknown Title",
            webpage_url=info.get("webpage_url") or info.get("original_url") or "",
            quality=self.state.parameter_values.get("quality", "Best Video+Audio"),
            subs=bool(self.state.parameter_values.get("subs", False)),
            path=str(self.state.output_options.output_dir),
        )
        self.state.download_counter += 1
        self.state.downloads.append(item)
        return item

    def run_workflow(self) -> tuple[bool, str, Path | None]:
        # Implementation of the download loop for the worker thread
        if not self.state.downloads and self.state.video_info:
            # If nothing in queue but we have info, add it first
            self.add_to_queue()
            
        if not self.state.downloads:
            return False, "No items in queue.", None

        if self.state.is_queue_running:
            return True, "Queue is already running.", None

        return True, "Starting downloads...", None

    def build_ydl_opts(
        self,
        item: DownloadItem,
        progress_hook: Optional[Callable] = None,
    ) -> dict:
        opts: Dict = {
            "outtmpl": f"{item.path}/%(title)s.%(ext)s",
            "quiet": True,
            "legacyserver_connect": True,
            "extractor_args": {"youtube": {"player_client": ["web", "android"]}},
        }
        if progress_hook:
            opts["progress_hooks"] = [progress_hook]

        fmt = QUALITY_MAP.get(item.quality, "bestvideo+bestaudio/best")

        if fmt == "__audio_mp3__":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
        elif fmt == "__audio_m4a__":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}]
        else:
            opts["format"] = fmt

        if item.subs:
            opts["writesubtitles"] = True
            opts["subtitleslangs"] = ["en", "ko", "auto"]

        return opts

    def download_item(self, item: DownloadItem, progress_hook: Callable) -> bool:
        if not HAS_YTDLP:
            return False
            
        opts = self.build_ydl_opts(item, progress_hook)
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([item.webpage_url])
        return True

    def reveal_output_dir(self) -> None:
        path = self.state.output_options.output_dir
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)
            
    def update_engine(self) -> str:
        import subprocess
        import sys
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return "OK"
        except Exception as e:
            raise RuntimeError(f"Update failed: {e}")
