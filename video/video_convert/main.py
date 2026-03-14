import os
import sys
import flet as ft
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = ROOT / "video" / "_engine"
SHARED_PATH = ROOT / "dev-tools" / "runtime" / "Shared"

sys.path.insert(0, str(ENGINE_ROOT))
sys.path.insert(0, str(ROOT / "dev-tools" / "runtime" / "Shared" / "src"))

from features.video.video_convert_state import VideoConvertState
from features.video.video_convert_flet import create_video_convert_app

def get_targets():
    # Basic target picking logic
    args = [a for a in sys.argv[1:] if a]
    if args:
        return [Path(a) for a in args if Path(a).exists()]
    
    # In a real environment, this might use a file picker if no args
    return []

def main():
    targets = get_targets()
    if not targets:
        # If no targets, we could show a file picker or just exit
        # For porting, we assume targets are passed or we show an empty list
        pass

    # Filter video files
    video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
    files = [p for p in targets if p.suffix.lower() in video_exts]
    
    state = VideoConvertState(files=files)
    app = create_video_convert_app(state)
    ft.app(target=app)

if __name__ == "__main__":
    main()
