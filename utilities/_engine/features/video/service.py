"""YouTube / Video downloader service – UI-free business logic."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, Dict, List, Optional

# ── yt-dlp dependency gating ──
try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    yt_dlp = None
    HAS_YTDLP = False

# ── paths ──
_FEATURES_ROOT = Path(__file__).resolve().parent.parent.parent  # _engine root
CONFIG_DIR = _FEATURES_ROOT / "config"
USERDATA_DIR = _FEATURES_ROOT / "userdata"
HISTORY_FILE = USERDATA_DIR / "download_history.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
LEGACY_HISTORY_FILES = [
    _FEATURES_ROOT / "config" / "runtime" / "download_history.json",
    _FEATURES_ROOT / "config" / "download_history.json",
]

# ── quality mapping ──
QUALITY_MAP = {
    "Best Video+Audio": "bestvideo+bestaudio/best",
    "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "Audio Only (MP3)": "__audio_mp3__",
    "Audio Only (M4A)": "__audio_m4a__",
}

_history_lock = threading.Lock()


# ── settings ──

def load_settings() -> dict:
    defaults = {"download_path": os.getcwd()}
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
        except Exception:
            pass
    return defaults


def save_settings(settings: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)


# ── history ──

def migrate_download_history() -> None:
    if HISTORY_FILE.exists():
        return
    for legacy_path in LEGACY_HISTORY_FILES:
        if legacy_path.exists():
            try:
                USERDATA_DIR.mkdir(parents=True, exist_ok=True)
                shutil.move(str(legacy_path), str(HISTORY_FILE))
            except Exception:
                pass
            return


def load_download_history() -> List[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_download_history(history: List[dict]) -> None:
    try:
        USERDATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


def record_download_history(info: dict, opts: dict) -> None:
    try:
        entry = {
            "title": info.get("title") or "Unknown Title",
            "url": info.get("webpage_url") or info.get("original_url") or "",
            "path": opts.get("path") or "",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quality": opts.get("quality") or "",
        }
        with _history_lock:
            history = load_download_history()
            history.insert(0, entry)
            history = history[:100]
            _save_download_history(history)
    except Exception:
        pass


# ── analysis ──

def analyze_url(url: str) -> dict:
    """Analyze a video URL and return metadata.

    Raises:
        RuntimeError: On analysis failure.
        ImportError: If yt-dlp is unavailable.
    """
    if not HAS_YTDLP:
        raise ImportError("yt-dlp is not installed. Please run setup.")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "legacyserver_connect": True,
        "extractor_args": {"youtube": {"player_client": ["web", "android"]}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info
    except Exception as e:
        raise RuntimeError(str(e))


# ── thumbnail ──

def fetch_thumbnail_bytes(url: str, max_size: tuple = (160, 90)) -> Optional[bytes]:
    """Fetch thumbnail and return resized JPEG bytes."""
    try:
        from PIL import Image

        with urllib.request.urlopen(url) as u:
            raw = u.read()
        img = Image.open(BytesIO(raw))
        img.thumbnail(max_size)
        buf = BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception:
        return None


# ── download ──

def build_ydl_opts(
    quality_key: str,
    subs: bool,
    download_path: str,
    progress_hook: Optional[Callable] = None,
) -> dict:
    """Build yt-dlp options dict from user selections."""
    opts: Dict = {
        "outtmpl": f"{download_path}/%(title)s.%(ext)s",
        "quiet": True,
        "legacyserver_connect": True,
        "extractor_args": {"youtube": {"player_client": ["web", "android"]}},
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    fmt = QUALITY_MAP.get(quality_key, "bestvideo+bestaudio/best")

    if fmt == "__audio_mp3__":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    elif fmt == "__audio_m4a__":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}]
    else:
        opts["format"] = fmt

    if subs:
        opts["writesubtitles"] = True
        opts["subtitleslangs"] = ["en", "ko", "auto"]

    return opts


def download_video(
    url: str,
    ydl_opts: dict,
) -> bool:
    """Download a video. Returns True on success.

    Raises:
        RuntimeError: On download failure.
        ImportError: If yt-dlp is unavailable.
    """
    if not HAS_YTDLP:
        raise ImportError("yt-dlp is not installed.")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return True


def update_engine() -> str:
    """Update yt-dlp via pip. Returns status message."""
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "OK"
    except Exception as e:
        raise RuntimeError(f"Update failed: {e}")
