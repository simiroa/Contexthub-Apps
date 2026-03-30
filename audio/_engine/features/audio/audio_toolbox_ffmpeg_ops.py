from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from contexthub.utils.external_tools import get_ffmpeg
from contexthub.utils.files import get_safe_path


def parse_timecode(raw: str) -> float | None:
    text = (raw or "").strip()
    if not text:
        return None
    parts = text.split(":")
    try:
        if len(parts) == 1:
            return max(0.0, float(parts[0]))
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return max(0.0, minutes * 60 + seconds)
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return max(0.0, hours * 3600 + minutes * 60 + seconds)
    except ValueError as exc:
        raise ValueError(f"Invalid trim time: {raw}") from exc
    raise ValueError(f"Invalid trim time: {raw}")


def build_trimmed_input(
    source_path: Path,
    trim_start: str,
    trim_end: str,
) -> tuple[Path, tempfile.TemporaryDirectory[str], subprocess.Popen | None]:
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for trim processing.")
    start_time = parse_timecode(trim_start)
    end_time = parse_timecode(trim_end)
    if start_time is None and end_time is None:
        raise RuntimeError("Trim is enabled but no start or end time is set.")
    if start_time is not None and end_time is not None and end_time <= start_time:
        raise RuntimeError("Trim end must be greater than trim start.")

    temp_dir = tempfile.TemporaryDirectory(prefix="audio_toolbox_trim_")
    trimmed_path = Path(temp_dir.name) / f"{source_path.stem}_trim.wav"
    cmd = [ffmpeg, "-y"]
    if start_time is not None:
        cmd.extend(["-ss", str(start_time)])
    cmd.extend(["-i", str(source_path)])
    if end_time is not None:
        if start_time is not None:
            cmd.extend(["-t", str(end_time - start_time)])
        else:
            cmd.extend(["-to", str(end_time)])
    cmd.extend(["-vn", "-acodec", "pcm_s16le", str(trimmed_path)])
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    _stdout, stderr = process.communicate()
    if process.returncode != 0 or not trimmed_path.exists():
        temp_dir.cleanup()
        raise RuntimeError((stderr or "").strip() or "Trim export failed")
    return trimmed_path, temp_dir, process


def run_ffmpeg_compress(
    input_path: Path,
    output_path: Path,
    fmt: str,
    level: str,
    copy_metadata: bool,
) -> subprocess.Popen | None:
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg not found")
    cmd = [ffmpeg, "-i", str(input_path)]
    if fmt == "mp3":
        cmd.extend(["-acodec", "libmp3lame", "-b:a", {"Quality": "256k", "Balanced": "192k", "Small": "128k"}[level]])
    elif fmt in {"m4a", "aac"}:
        cmd.extend(["-acodec", "aac", "-b:a", {"Quality": "256k", "Balanced": "192k", "Small": "128k"}[level]])
    elif fmt == "ogg":
        cmd.extend(["-acodec", "libvorbis", "-q:a", {"Quality": "6", "Balanced": "4", "Small": "2"}[level]])
    else:
        raise RuntimeError(f"Unsupported compression format: {fmt}")
    if not copy_metadata:
        cmd.extend(["-map_metadata", "-1"])
    cmd.extend(["-y", str(output_path)])
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    _stdout, stderr = process.communicate()
    if process.returncode != 0 or not output_path.exists():
        raise RuntimeError((stderr or "").strip() or "Compression failed")
    return process


def run_ffmpeg_enhance(
    input_path: Path,
    output_path: Path,
    profile: str,
    fmt: str,
    copy_metadata: bool,
) -> subprocess.Popen | None:
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg not found")
    filters = {
        "Speech Clean": "highpass=f=70,lowpass=f=13500,afftdn=nf=-18,acompressor=threshold=-18dB:ratio=2.2:attack=15:release=180,alimiter=limit=0.97",
        "Clarity": "highpass=f=60,equalizer=f=3200:t=q:w=1.2:g=3,acompressor=threshold=-20dB:ratio=2:attack=20:release=180,alimiter=limit=0.97",
        "Presence": "highpass=f=70,equalizer=f=4500:t=q:w=1.0:g=4,equalizer=f=180:t=q:w=0.8:g=-2,acompressor=threshold=-19dB:ratio=2.2:attack=18:release=180,alimiter=limit=0.97",
    }[profile]
    cmd = [ffmpeg, "-i", str(input_path), "-af", filters]
    if fmt == "wav":
        cmd.extend(["-acodec", "pcm_s16le"])
    elif fmt == "flac":
        cmd.extend(["-acodec", "flac"])
    elif fmt == "m4a":
        cmd.extend(["-acodec", "aac", "-b:a", "256k"])
    elif fmt == "mp3":
        cmd.extend(["-acodec", "libmp3lame", "-b:a", "256k"])
    else:
        raise RuntimeError(f"Unsupported enhance format: {fmt}")
    if not copy_metadata:
        cmd.extend(["-map_metadata", "-1"])
    cmd.extend(["-y", str(output_path)])
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    _stdout, stderr = process.communicate()
    if process.returncode != 0 or not output_path.exists():
        raise RuntimeError((stderr or "").strip() or "Enhance failed")
    return process


def output_path_with_suffix(output_dir: Path, stem: str, suffix: str, extension: str) -> Path:
    return get_safe_path(output_dir / f"{stem}{suffix}.{extension}")
