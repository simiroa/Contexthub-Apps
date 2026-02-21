"""
Subtitle Generation using Faster-Whisper.
"""
import sys
import os
import argparse
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.files import get_safe_path
from utils import paths

# Fix for OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Force UTF-8 output for Windows console
sys.stdout.reconfigure(encoding='utf-8')

from faster_whisper import WhisperModel
import json

def format_timestamp(seconds, fmt="srt"):
    """Format seconds to timestamp."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    if fmt == "vtt":
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

def save_subtitles(segments, info, video_path, output_formats=["srt"], task="transcribe", output_dir=None):
    """Save subtitles in multiple formats."""
    saved_paths = []
    
    # We need to iterate segments for each format, or cache them.
    # Since we passed a list 'segments', we can iterate it multiple times.
    
    for fmt in output_formats:
        suffix = f".{info.language}.{fmt}"
        if task == "translate":
            suffix = f".en.{fmt}"
            
        if output_dir:
            out_root = Path(output_dir)
            out_root.mkdir(parents=True, exist_ok=True)
            output_path = get_safe_path(out_root / (Path(video_path).stem + suffix))
        else:
            output_path = get_safe_path(Path(video_path).with_suffix(suffix))
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                if fmt == "srt":
                    for i, segment in enumerate(segments, start=1):
                        start = format_timestamp(segment.start, "srt")
                        end = format_timestamp(segment.end, "srt")
                        text = segment.text.strip()
                        f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
                        
                elif fmt == "vtt":
                    f.write("WEBVTT\n\n")
                    for segment in segments:
                        start = format_timestamp(segment.start, "vtt")
                        end = format_timestamp(segment.end, "vtt")
                        text = segment.text.strip()
                        f.write(f"{start} --> {end}\n{text}\n\n")
                        
                elif fmt == "txt":
                    for segment in segments:
                        text = segment.text.strip()
                        f.write(f"{text}\n")
                        
                elif fmt == "json":
                    data = []
                    for segment in segments:
                        item = {
                            "start": segment.start,
                            "end": segment.end,
                            "text": segment.text.strip()
                        }
                        data.append(item)
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"Saved: {output_path}")
            saved_paths.append(str(output_path))
            
        except Exception as e:
            print(f"Error saving {fmt}: {e}")

    return saved_paths

def generate_subtitles(video_path, model_size="small", device="cuda", compute_type="float16", task="transcribe", language=None, output_formats=["srt"], output_dir=None):
    """Generate subtitles for video."""
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
        except Exception as e:
            print(f"Error loading model on {device}: {e}")
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
                raise e
        
        print(f"Processing {video_path}...")
        segments, info = model.transcribe(video_path, beam_size=5, task=task, language=language)
        
        print(f"Detected language '{info.language}' with probability {info.language_probability}")
        
        # Collect all segments first
        all_segments = list(segments)
        
        # Print preview to console (just text)
        for segment in all_segments:
             start = format_timestamp(segment.start, "srt")
             end = format_timestamp(segment.end, "srt")
             print(f"[{start} --> {end}] {segment.text.strip()}", flush=True)

        save_subtitles(all_segments, info, video_path, output_formats, task, output_dir)
        return True
        
    except Exception as e:
        print(f"Error generating subtitles: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Subtitle Generation Tool')
    parser.add_argument('video_path', help='Input video path')
    parser.add_argument('--model', default='small', choices=['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3'], help='Model size')
    parser.add_argument('--device', default='cuda', choices=['cuda', 'cpu'], help='Device to use')
    parser.add_argument('--task', default='transcribe', choices=['transcribe', 'translate'], help='Task (transcribe or translate to English)')
    parser.add_argument('--lang', help='Source language (optional)')
    parser.add_argument('--format', default='srt', help='Output formats (comma-separated, e.g. srt,txt)')
    parser.add_argument('--output_dir', help='Output directory (optional)')
    
    args = parser.parse_args()
    
    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"Error: File not found: {video_path}")
        return 1
    
    # Parse formats
    formats = [f.strip() for f in args.format.split(',')]
        
    success = generate_subtitles(
        str(video_path),
        model_size=args.model,
        device=args.device,
        task=args.task,
        language=args.lang,
        output_formats=formats,
        output_dir=args.output_dir
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
