import sys
import argparse
import cv2
import numpy as np
import torch
import warnings
from pathlib import Path

# Suppress warnings
warnings.filterwarnings("ignore")

# Add engine to path to import utils
ENGINE_DIR = Path(__file__).resolve().parents[3] # standalone -> ai -> features -> _engine
sys.path.append(str(ENGINE_DIR))
from utils import paths

# Add libs to path
sys.path.append(str(ENGINE_DIR / "libs"))

# --- Monkey Patch for BasicSR compatibility with torchvision >= 0.17 ---
import torchvision
import torchvision.transforms as transforms
if not hasattr(transforms, 'functional_tensor'):
    transforms.functional_tensor = transforms.functional
# Also patch sys.modules to handle 'from torchvision.transforms import functional_tensor'
sys.modules['torchvision.transforms.functional_tensor'] = transforms.functional
# ----------------------------------------------------------------------

# Remove top-level basicsr/realesrgan imports to avoid early trigger
# We will use lazy loading inside upscale_batch instead.

def ensure_model(model_name):
    """Download model if not exists using setup utility."""
    if model_name == "RealESRGAN_x4plus":
        try:
            from setup.download_models import download_realesrgan
            download_realesrgan()
        except ImportError:
            # Fallback pathing
            sys.path.append(str(ENGINE_DIR))
            from setup.download_models import download_realesrgan
            download_realesrgan()
            
    model_path = paths.REALESRGAN_DIR / f"{model_name}.pth"
    if not model_path.exists():
        # Last ditch: try to see if it's in the root
        if (ENGINE_DIR / f"{model_name}.pth").exists():
             return str(ENGINE_DIR / f"{model_name}.pth")
        raise FileNotFoundError(f"Model {model_name} could not be downloaded to {model_path}")
        
    return str(model_path)

def upscale_batch(input_paths, output_dir=None, scale=4, face_enhance=False, tile_size=0):
    """
    Upscale multiple images using a single model load session.
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Initializing AI Session on: {device}")
    
    # Lazy imports inside the function to speed up script activation
    try:
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
        from gfpgan import GFPGANer
    except ImportError as e:
        print(f"Error: Missing AI libraries. Please ensure 'ai' environment is correct. ({e})")
        return False

    # Load Real-ESRGAN model
    model_name = 'RealESRGAN_x4plus'
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    
    # Get model path
    try:
        model_path = ensure_model(model_name)
    except Exception as e:
        print(f"Model Error: {e}")
        return False
    
    print(f"Loading Models...")
    upsampler = RealESRGANer(
        scale=4,
        model_path=model_path,
        model=model,
        tile=tile_size,
        tile_pad=10,
        pre_pad=0,
        half=True if device.type == 'cuda' else False,
        device=device,
    )
    
    face_enhancer = None
    if face_enhance:
        gfpgan_path = paths.REALESRGAN_DIR / "GFPGANv1.4.pth"
        if not gfpgan_path.exists():
             from setup.download_models import download_realesrgan
             download_realesrgan()
             
        face_enhancer = GFPGANer(
            model_path=str(gfpgan_path),
            upscale=scale,
            arch='clean',
            channel_multiplier=2,
            bg_upsampler=upsampler
        )

    total = len(input_paths)
    for i, input_path_str in enumerate(input_paths, 1):
        input_path = Path(input_path_str)
        if not input_path.exists():
            print(f"[{i}/{total}] Skip: File not found: {input_path}")
            continue

        if output_dir:
            output_path = Path(output_dir) / f"{input_path.stem}_upscaled.png"
        else:
            suffix = "_upscaled"
            if face_enhance: suffix += "_face"
            output_path = input_path.with_name(f"{input_path.stem}{suffix}.png")

        print(f"[{i}/{total}] Processing: {input_path.name}")
        
        try:
            img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
            if img is None:
                print(f"  Error: Failed to read image")
                continue

            if face_enhance:
                _, _, output = face_enhancer.enhance(img, has_aligned=False, only_center_face=False, paste_back=True)
            else:
                output, _ = upsampler.enhance(img, outscale=scale)
            
            cv2.imwrite(str(output_path), output)
            print(f"  ✓ Saved: {output_path.name}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            if "CUDA out of memory" in str(e):
                print("  ! VRAM Full. Try enabling Tiling Mode.")
    
    # Cleanup
    if device.type == 'cuda':
        torch.cuda.empty_cache()
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Advanced AI Upscaling (Batch Supported)')
    parser.add_argument('input_paths', nargs='+', help='One or more input image paths')
    parser.add_argument('--output_dir', help='Output directory (optional)')
    parser.add_argument('--scale', type=float, default=4, help='Upscale factor (default: 4)')
    parser.add_argument('--face-enhance', action='store_true', help='Enable face enhancement')
    parser.add_argument('--tile', type=int, default=0, help='Tile size (0 for auto)')
    
    args = parser.parse_args()
    
    upscale_batch(
        args.input_paths,
        output_dir=args.output_dir,
        scale=args.scale,
        face_enhance=args.face_enhance,
        tile_size=args.tile
    )

if __name__ == "__main__":
    sys.exit(main())
