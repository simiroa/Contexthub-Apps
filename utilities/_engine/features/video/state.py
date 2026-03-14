"""YouTube / Video downloader – application state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DownloadItem:
    """Represents a single download task in the queue."""
    id: int = 0
    title: str = ""
    progress: float = 0.0
    status: str = "queued"          # queued | starting | downloading | complete | failed
    status_text: str = ""           # human-readable text


@dataclass
class VideoDownloaderState:
    url: str = ""
    video_info: Optional[dict] = None
    quality: str = "Best Video+Audio"
    subs: bool = False
    download_path: str = ""

    # analysis
    is_analyzing: bool = False

    # downloads
    downloads: List[DownloadItem] = field(default_factory=list)
    download_counter: int = 0
    is_queue_running: bool = False

    # thumb
    thumbnail_b64: str = ""

    # error
    error: Optional[str] = None
