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

from features.video.video_audio_state import VideoAudioState
from features.video.video_audio_flet import create_video_audio_app

def get_targets():
    args = [a for a in sys.argv[1:] if a]
    if args:
        return [Path(a) for a in args if Path(a).exists()]
    return []

def main():
    targets = get_targets()
    video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
    files = [p for p in targets if p.suffix.lower() in video_exts]
    
    state = VideoAudioState(files=files, mode="extract")
    app = create_video_audio_app(state)
    ft.app(target=app)

if __name__ == "__main__":
    main()
