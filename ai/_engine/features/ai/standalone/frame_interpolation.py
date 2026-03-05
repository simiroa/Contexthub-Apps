"""
Frame interpolation using FFmpeg minterpolate filter.
Fast and reliable alternative to RIFE.
"""
import sys
import argparse
from pathlib import Path
import subprocess

# Add src to path to import utils
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.external_tools import get_ffmpeg

def get_video_info(input_path):
    """Get video information using FFprobe."""
    ffmpeg = get_ffmpeg()
    ffprobe = ffmpeg.replace("ffmpeg.exe", "ffprobe.exe")
    
    if not Path(ffprobe).exists():
        # Fallback to system ffprobe if not found next to ffmpeg
        ffprobe = "ffprobe"
    
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,width,height",
        "-of", "default=noprint_wrappers=1",
        str(input_path)
    ]
    
    info = {'fps': 30.0, 'width': 0, 'height': 0, 'has_audio': False}
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            if '=' in line:
                key, value = line.split('=')
                info[key] = value
        
        # Parse FPS
        if 'r_frame_rate' in info:
            num, den = info['r_frame_rate'].split('/')
            if float(den) > 0:
                info['fps'] = float(num) / float(den)
                
        # Check for audio stream
        cmd_audio = [
            ffprobe,
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1",
            str(input_path)
        ]
        result_audio = subprocess.run(cmd_audio, capture_output=True, text=True)
        if "codec_type=audio" in result_audio.stdout:
            info['has_audio'] = True
            
        return info
    except Exception as e:
        print(f"Warning: Failed to get video info: {e}")
        return info

def interpolate_video_ffmpeg(input_path, output_path, target_fps=60, method="mci"):
    """
    Interpolate video frames using FFmpeg.
    """
    ffmpeg = get_ffmpeg()
    
    print(f"Using FFmpeg: {ffmpeg}")
    
    # Get input video info
    info = get_video_info(input_path)
    input_fps = info.get('fps', 30)
    width = info.get('width', 'unknown')
    height = info.get('height', 'unknown')
    has_audio = info.get('has_audio', False)
    
    print(f"Input: {input_fps:.2f} FPS, {width}x{height}, Audio: {has_audio}")
    print(f"Target: {target_fps} FPS")
    print(f"Method: {method.upper()}")
    
    # Build FFmpeg command
    if method == "mci":
        # Motion Compensated Interpolation (best quality)
        # scd=none: disable scene change detection to prevent stutter on some clips
        filter_complex = f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none"
    else:
        # Simple blend interpolation (faster)
        filter_complex = f"minterpolate=fps={target_fps}:mi_mode=blend"
    
    # Build FFmpeg command
    cmd = [
        ffmpeg,
        "-i", str(input_path),
        "-vf", filter_complex,
        "-c:v", "libx264",            # Use CPU encoding for maximum compatibility
        "-preset", "medium",
        "-crf", "20",                 # High quality
        "-pix_fmt", "yuv420p",        # Ensure compatibility
        "-y"
    ]
    
    if has_audio:
        cmd.extend(["-c:a", "copy"])
    
    cmd.append(str(output_path))
    
    print(f"\nProcessing (this may take a while)...")
    
    # Run FFmpeg
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # Merge stderr to stdout
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # Stream output
    for line in process.stdout:
        print(line, end='')
        

        


def main():
    parser = argparse.ArgumentParser(description='Video Frame Interpolation (FFmpeg)')
    parser.add_argument('input_path', help='Input video path')
    parser.add_argument('--output', help='Output path (optional)')
    parser.add_argument('--fps', type=int, default=None, help='Target FPS (optional, overrides multiplier)')
    parser.add_argument('--multiplier', type=int, default=2, choices=[2, 3, 4],
                       help='FPS multiplier: 2x, 3x, or 4x (default: 2)')
    parser.add_argument('--method', choices=['mci', 'blend'], default='mci',
                       help='Interpolation method: mci (best) or blend (fast)')
    
    args = parser.parse_args()
    
    input_path = Path(args.input_path)
    if not input_path.exists():
        print(f"Error: Video not found: {input_path}")
        return 1
        
    # Check file size
    if input_path.stat().st_size == 0:
        print(f"Error: Input file is empty: {input_path}")
        return 1
    
    # Calculate target FPS
    if args.fps:
        target_fps = args.fps
    else:
        # Auto-detect input FPS and multiply
        info = get_video_info(str(input_path))
        input_fps = info.get('fps', 30)
        target_fps = int(input_fps * args.multiplier)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(f"{input_path.stem}_{args.multiplier}x.mp4")
    
    try:
        success = interpolate_video_ffmpeg(
            str(input_path),
            str(output_path),
            target_fps=target_fps,
            method=args.method
        )
        return 0 if success else 1
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
