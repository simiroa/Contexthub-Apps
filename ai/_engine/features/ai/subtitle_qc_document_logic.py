from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from contexthub.ui.qt.shell import qt_t

from features.ai.subtitle_qc_state import SubtitleDocument, SubtitleSegment


SUPPORTED_FORMATS = {"srt", "vtt", "txt"}
TIMESTAMP_RE = re.compile(r"(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d+)(?:[.,](?P<ms>\d{1,3}))?")
INLINE_RANGE_RE = re.compile(
    r"^\s*\[(?P<start>\d+:\d{2}:\d+(?:[.,]\d{1,3})?)(?:\s*-\s*(?P<end>\d+:\d{2}:\d+(?:[.,]\d{1,3})?))?\]\s*(?P<text>.*)$"
)


def to_float_timestamp(value: str) -> float:
    value = value.strip()
    if not value:
        raise ValueError(qt_t("subtitle_qc.timestamp_empty", "Empty timestamp"))
    match = TIMESTAMP_RE.match(value)
    if not match:
        raise ValueError(qt_t("subtitle_qc.timestamp_invalid", "Invalid timestamp: {value}", value=value))
    parts = match.groupdict()
    seconds = float(parts["s"])
    milliseconds = parts.get("ms") or "0"
    if len(milliseconds) == 1:
        milliseconds = f"{milliseconds}00"
    elif len(milliseconds) == 2:
        milliseconds = f"{milliseconds}0"
    return int(parts["h"]) * 3600 + int(parts["m"]) * 60 + seconds + int(milliseconds[:3]) / 1000.0


def coerce_output_formats(formats: list[str] | None) -> list[str]:
    if not formats:
        return ["srt", "vtt", "txt"]
    cleaned = [str(fmt).strip().lower() for fmt in formats if str(fmt).strip()]
    cleaned = [fmt for fmt in cleaned if fmt in SUPPORTED_FORMATS]
    return cleaned or ["srt", "vtt", "txt"]


def format_timestamp(seconds: float, fmt: str = "srt") -> str:
    total = max(0.0, float(seconds))
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    sec = total % 60
    milliseconds = int((sec - int(sec)) * 1000)
    if fmt == "vtt":
        return f"{hours:02d}:{minutes:02d}:{int(sec):02d}.{milliseconds:03d}"
    return f"{hours:02d}:{minutes:02d}:{int(sec):02d},{milliseconds:03d}"


def normalize_segment_payload(raw_segments: list[dict[str, Any]]) -> list[SubtitleSegment]:
    normalized: list[SubtitleSegment] = []
    for index, entry in enumerate(raw_segments):
        text = str(entry.get("text", "")).strip()
        if not text:
            continue
        start = float(entry.get("start", 0.0))
        end = float(entry.get("end", 0.0))
        if end < start:
            start, end = end, start
        normalized.append(SubtitleSegment(segment_id=index, start=start, end=end, text=text))
    if not normalized:
        raise ValueError(qt_t("subtitle_qc.no_segments", "No valid subtitle segments"))
    return normalized


def parse_transcript_text(text: str) -> list[SubtitleSegment]:
    normalized: list[SubtitleSegment] = []
    for index, raw_line in enumerate(text.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        match = INLINE_RANGE_RE.match(line)
        if match:
            start = to_float_timestamp(match.group("start"))
            end_text = match.group("end")
            end = to_float_timestamp(end_text) if end_text else start
            body = match.group("text").strip()
            if body:
                normalized.append(
                    SubtitleSegment(
                        segment_id=len(normalized),
                        start=min(start, end),
                        end=max(start, end),
                        text=body,
                        is_generated=False,
                    )
                )
            continue
        normalized.append(
            SubtitleSegment(
                segment_id=len(normalized),
                start=0.0,
                end=0.0,
                text=line,
                is_generated=False,
            )
        )
    if not normalized:
        raise ValueError(qt_t("meeting_notes.no_transcript", "No transcript text to save"))
    return normalized


def analyze_document(document: SubtitleDocument) -> tuple[list[str], str]:
    issues: list[str] = []
    previous_end = -1.0
    for index, segment in enumerate(document.segments, start=1):
        flags: list[str] = []
        text = segment.text.strip()
        duration = max(0.0, segment.end - segment.start)
        if not text:
            flags.append("empty_text")
        if duration < 0.7:
            flags.append("too_short")
        if duration > 8.0:
            flags.append("too_long")
        if previous_end >= 0 and segment.start < previous_end:
            flags.append("overlap")
        chars_per_second = len(text.replace(" ", "")) / max(duration, 0.01)
        if chars_per_second > 24:
            flags.append("dense_text")
        segment.review_flags = flags
        for flag in flags:
            issues.append(f"[{index}] {flag.replace('_', ' ')}")
        previous_end = max(previous_end, segment.end)

    probability = document.language_probability or 0.0
    if issues:
        confidence = "low" if len(issues) > 4 else "medium"
    elif probability >= 0.8:
        confidence = "high"
    elif probability > 0:
        confidence = "medium"
    else:
        confidence = "pending"

    document.issue_messages = issues
    return issues, confidence


def write_segments_to_file(asset: Path, document: SubtitleDocument, fmt: str, output_dir: Path, stem: str) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "txt":
        target = output_dir / f"{stem}.txt"
    elif fmt == "vtt":
        target = output_dir / f"{stem}.{document.generated_language or 'en'}.vtt"
    else:
        target = output_dir / f"{stem}.{document.generated_language or 'en'}.srt"

    with open(target, "w", encoding="utf-8") as stream:
        if fmt == "srt":
            for index, segment in enumerate(document.segments, start=1):
                stream.write(f"{index}\n")
                stream.write(f"{format_timestamp(segment.start, 'srt')} --> {format_timestamp(segment.end, 'srt')}\n")
                stream.write(f"{segment.text}\n\n")
        elif fmt == "vtt":
            stream.write("WEBVTT\n\n")
            for segment in document.segments:
                stream.write(f"{format_timestamp(segment.start, 'vtt')} --> {format_timestamp(segment.end, 'vtt')}\n")
                stream.write(f"{segment.text}\n\n")
        else:
            for segment in document.segments:
                stream.write(f"{segment.text}\n")
    return str(target)
