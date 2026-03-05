import os
import sys
import urllib.request
import torch
from pathlib import Path

# Try to import paths from the app's utils
try:
    current_dir = Path(__file__).resolve().parent
    engine_dir = current_dir.parent
    sys.path.append(str(engine_dir))
    from utils import paths
except ImportError:
    # Fallback if import fails
    class Paths:
        ENGINE_DIR = Path(__file__).resolve().parents[1]
        RESOURCES_DIR = ENGINE_DIR / "resources"
        AI_MODELS_DIR = RESOURCES_DIR / "ai_models"
        MARIGOLD_DIR = AI_MODELS_DIR / "marigold"
        REALESRGAN_DIR = AI_MODELS_DIR / "realesrgan"
        WHISPER_DIR = AI_MODELS_DIR / "whisper"
        BIREFNET_DIR = AI_MODELS_DIR / "BiRefNet"
    paths = Paths()

def download_file(url, dest, label="Model"):
    """Download file with User-Agent and progress if possible."""
    print(f"Downloading {label} from {url}...")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response, open(dest, 'wb') as out_file:
            # Simple progress log
            content_length = response.getheader('Content-Length')
            if content_length:
                total_size = int(content_length)
                downloaded = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    # print(f"Progress: {downloaded/total_size:.1%}", end='\r')
            else:
                out_file.write(response.read())
        print(f"✓ {label} saved to {dest}")
        return True
    except Exception as e:
        print(f"✗ Failed to download {label}: {e}")
        return False

def download_realesrgan():
    """Download standard Real-ESRGAN and GFPGAN models."""
    models = {
        "RealESRGAN_x4plus.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        "GFPGANv1.4.pth": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth"
    }
    
    success = True
    for name, url in models.items():
        dest = paths.REALESRGAN_DIR / name
        if not dest.exists():
            if not download_file(url, dest, name):
                success = False
    return success

def download_marigold():
    """Download Marigold models (Depth, Normals, Intrinsics)."""
    print("\n--- Downloading Marigold Suite (v1.1) ---")
    try:
        from diffusers import MarigoldDepthPipeline, MarigoldNormalsPipeline, MarigoldIntrinsicsPipeline
        
        # Ensure cache is configured
        if hasattr(paths, 'configure_caches'):
            paths.configure_caches()
            
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        repos = [
            ("prs-eth/marigold-depth-v1-1", MarigoldDepthPipeline),
            ("prs-eth/marigold-normals-v1-1", MarigoldNormalsPipeline),
            ("prs-eth/marigold-iid-appearance-v1-1", MarigoldIntrinsicsPipeline),
        ]
        
        for repo_id, pipe_class in repos:
            print(f"Fetching {repo_id} via {pipe_class.__name__}...")
            pipe_class.from_pretrained(repo_id, torch_dtype=dtype)
            
        print("✓ Marigold Suite ready.")
        return True
    except Exception as e:
        print(f"✗ Marigold download failed: {e}")
        return False

def download_whisper(model_size="small"):
    """Download Faster-Whisper models."""
    print(f"\n--- Downloading Whisper {model_size} Model ---")
    try:
        from faster_whisper import WhisperModel
        # This will download/verify models in the standardized WHISPER_DIR
        WhisperModel(
            model_size,
            device="cpu", # Force CPU for just downloading
            compute_type="int8",
            download_root=str(paths.WHISPER_DIR)
        )
        print(f"✓ Whisper {model_size} ready in {paths.WHISPER_DIR}")
        return True
    except Exception as e:
        print(f"✗ Whisper download failed: {e}")
        return False

def download_bg_rm():
    """Download BiRefNet background removal model."""
    print("\n--- Downloading BiRefNet (Background Removal) ---")
    try:
        from transformers import AutoModelForImageSegmentation
        model_id = "ZhengPeng7/BiRefNet"
        
        # Ensure cache is configured
        if hasattr(paths, 'configure_caches'):
            paths.configure_caches()
            
        print(f"Fetching {model_id} via transformers...")
        AutoModelForImageSegmentation.from_pretrained(model_id, trust_remote_code=True)
        print("✓ BiRefNet ready.")
        return True
    except Exception as e:
        print(f"✗ BiRefNet download failed: {e}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--marigold", action="store_true")
    parser.add_argument("--upscale", action="store_true")
    parser.add_argument("--bgrm", action="store_true")
    parser.add_argument("--whisper", help="model size")
    
    args = parser.parse_args()
    
    if args.marigold: download_marigold()
    if args.upscale: download_realesrgan()
    if args.bgrm: download_bg_rm()
    if args.whisper: download_whisper(args.whisper)

if __name__ == "__main__":
    main()
