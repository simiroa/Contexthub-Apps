from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DownloadItem:
    """Represents a single download task in the queue."""
    id: int = 0
    title: str = ""
    webpage_url: str = ""
    quality: str = "Best Video+Audio"
    subs: bool = False
    path: str = ""
    progress: float = 0.0
    status: str = "queued"          # queued | starting | downloading | complete | failed
    status_text: str = ""           # human-readable text


@dataclass
class OutputOptions:
    output_dir: Path = Path.home() / "Downloads"
    file_prefix: str = "yt_dl" # Not directly used for filename but for template
    open_folder_after_run: bool = True
    export_session_json: bool = False


@dataclass
class YoutubeDownloaderState:
    # URL and Analysis
    url: str = ""
    video_info: Optional[dict] = None
    thumbnail_b64: str = ""
    is_analyzing: bool = False
    
    # Parameters
    workflow_name: str = "Best Video+Audio" # Using this to store quality selection
    workflow_description: str = "YouTube / Video Downloader"
    subs: bool = False
    
    # Downloads Queue
    input_assets: list[any] = field(default_factory=list) # Matching template naming but for downloads
    downloads: List[DownloadItem] = field(default_factory=list)
    download_counter: int = 0
    is_queue_running: bool = False
    
    # Global Parameters (UI compatibility)
    parameter_values: dict[str, object] = field(default_factory=dict)
    output_options: OutputOptions = field(default_factory=OutputOptions)
    
    # Status
    status_text: str = ""
    detail_text: str = ""
    progress: float = 0.0
    errors: List[str] = field(default_factory=list)
