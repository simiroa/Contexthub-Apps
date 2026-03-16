"""
Subtitle generation using faster-whisper.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.files import get_safe_path
from utils import paths

from faster_whisper import WhisperModel

# Fix for OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def format_timestamp(seconds: float, fmt: str = "srt") -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = float(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    if fmt == "vtt":
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"


def _resolve_segment_fields(segment) -> tuple[float, float, str]:
    start = float(getattr(segment, "start", 0.0))
    end = float(getattr(segment, "end", 0.0))
    text = str(getattr(segment, "text", "")).strip()
    return start, end, text


def save_subtitles(segments, info, video_path, output_formats=("srt",), task="transcribe", output_dir=None):
    saved_paths = []
    language = info["language"] if isinstance(info, dict) else str(getattr(info, "language", "en"))
    for fmt in output_formats:
        suffix = f".{language}.{fmt}"
        if task == "translate":
            suffix = f".en.{fmt}"

        if output_dir:
            out_root = Path(output_dir)
            out_root.mkdir(parents=True, exist_ok=True)
            output_path = get_safe_path(out_root / (Path(video_path).stem + suffix))
        else:
            output_path = get_safe_path(Path(video_path).with_suffix(suffix))

        try:
            with open(output_path, "w", encoding="utf-8") as file:
                if fmt == "srt":
                    for index, (start, end, text) in enumerate(( _resolve_segment_fields(segment) for segment in segments), start=1):
                        file.write(f"{index}\n{format_timestamp(start, 'srt')} --> {format_timestamp(end, 'srt')}\n{text}\n\n")
                elif fmt == "vtt":
                    file.write("WEBVTT\n\n")
                    for start, end, text in (_resolve_segment_fields(segment) for segment in segments):
                        file.write(f"{format_timestamp(start, 'vtt')} --> {format_timestamp(end, 'vtt')}\n{text}\n\n")
                elif fmt == "txt":
                    for start, end, text in (_resolve_segment_fields(segment) for segment in segments):
                        file.write(f"{text}\n")
                elif fmt == "json":
                    data = []
                    for start, end, text in (_resolve_segment_fields(segment) for segment in segments):
                        data.append({"start": start, "end": end, "text": text})
                    json.dump(data, file, ensure_ascii=False, indent=2)
            print(f"Saved: {output_path}")
            saved_paths.append(str(output_path))
        except Exception as exc:
            print(f"Error saving {fmt}: {exc}")

    return saved_paths


def _to_segment_payload(segments) -> list[dict[str, float | str]]:
    payload: list[dict[str, float | str]] = []
    for segment in segments:
        start, end, text = _resolve_segment_fields(segment)
        payload.append({"start": start, "end": end, "text": text})
    return payload


def generate_subtitles(
    video_path,
    model_size="small",
    device="cuda",
    compute_type="float16",
    task="transcribe",
    language=None,
    output_formats=("srt",),
    output_dir=None,
    return_result: bool = False,
):
    try:
        print(f"Loading model {model_size} on {device}...")
        if device == "cpu":
            compute_type = "int8"

        try:
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=str(paths.WHISPER_DIR),
            )
        except Exception as exc:
            print(f"Error loading model on {device}: {exc}")
            if device == "cuda":
                print("Falling back to CPU...")
                device = "cpu"
                compute_type = "int8"
                model = WhisperModel(
                    model_size,
                    device=device,
                    compute_type=compute_type,
                    download_root=str(paths.WHISPER_DIR),
                )
            else:
                raise

        print(f"Processing {video_path}...")
        segments, info = model.transcribe(video_path, beam_size=5, task=task, language=language)
        all_segments = list(segments)

        segment_payload = _to_segment_payload(all_segments)
        info_payload = {
            "language": str(getattr(info, "language", "unknown")),
            "language_probability": float(getattr(info, "language_probability", 0.0)),
            "duration": float(getattr(info, "duration", 0.0)),
            "task": task,
        }

        print(f"Detected language '{info_payload['language']}' with probability {info_payload['language_probability']}")
        for index, entry in enumerate(segment_payload, start=1):
            start = format_timestamp(float(entry["start"]), "srt")
            end = format_timestamp(float(entry["end"]), "srt")
            print(f"[{index}] {start} --> {end}: {entry['text']}", flush=True)

        output_paths = save_subtitles(all_segments, info_payload, video_path, output_formats, task, output_dir)

        if return_result:
            return {"success": True, "segments": segment_payload, "info": info_payload, "output_paths": output_paths}
        return True

    except Exception as exc:
        message = f"Error generating subtitles: {exc}"
        print(message)
        if return_result:
            return {"success": False, "error": message, "segments": [], "info": {}, "output_paths": []}
        return False


def main():
    parser = argparse.ArgumentParser(description="Subtitle Generation Tool")
    parser.add_argument("video_path", help="Input video path")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"], help="Model size")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"], help="Device to use")
    parser.add_argument(
        "--task",
        default="transcribe",
        choices=["transcribe", "translate"],
        help="Task (transcribe or translate to English)",
    )
    parser.add_argument("--lang", help="Source language (optional)")
    parser.add_argument("--format", default="srt", help="Output formats (comma-separated, e.g. srt,txt)")
    parser.add_argument("--output_dir", help="Output directory (optional)")
    args = parser.parse_args()

    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"Error: File not found: {video_path}")
        return 1

    formats = [fmt.strip() for fmt in args.format.split(",") if fmt.strip()]
    success = generate_subtitles(
        str(video_path),
        model_size=args.model,
        device=args.device,
        task=args.task,
        language=args.lang,
        output_formats=formats or ["srt"],
        output_dir=args.output_dir,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
