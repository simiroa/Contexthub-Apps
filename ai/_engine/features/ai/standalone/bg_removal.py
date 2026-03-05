"""
Background Removal script using BiRefNet or InSPyReNet.
Runs in the unified Python environment.
"""
import sys
import argparse
import torch
import numpy as np
from PIL import Image
from pathlib import Path
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Add engine to path to import utils
ENGINE_DIR = Path(__file__).resolve().parents[3]
sys.path.append(str(ENGINE_DIR))
from utils import paths

# --- Monkey Patch for BasicSR/torchvision compatibility ---
import torchvision
import torchvision.transforms as transforms
if not hasattr(transforms, 'functional_tensor'):
    transforms.functional_tensor = transforms.functional
sys.modules['torchvision.transforms.functional_tensor'] = transforms.functional
from transformers import AutoModelForImageSegmentation
# ---------------------------------------------------------

def remove_background_rmbg(image_path, output_path):
    """RMBG-2.0 (BriaAI) Implementation - Requires Auth."""
    from torchvision import transforms
    from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError, LocalTokenNotFoundError
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Loading RMBG-2.0 model...")
    
    # Check for local model in _engine/resources/ai_models/RMBG-2.0
    local_model_path = paths.AI_MODELS_DIR / "RMBG-2.0"
    
    model_id = "briaai/RMBG-2.0"
    
    try:
        if local_model_path.exists() and any(local_model_path.iterdir()):
            print(f"[Info] Using local model from: {local_model_path}")
            model = AutoModelForImageSegmentation.from_pretrained(local_model_path, trust_remote_code=True)
        else:
            print(f"[Info] Local model not found at {local_model_path}")
            print(f"Loading '{model_id}' from Hugging Face Cache...")
            model = AutoModelForImageSegmentation.from_pretrained(model_id, trust_remote_code=True, local_files_only=True)
    except OSError:
        print(f"\n[알림] '{model_id}' 모델 로드 중 (Download)...")
        try:
            model = AutoModelForImageSegmentation.from_pretrained(model_id, trust_remote_code=True)
        except (GatedRepoError, LocalTokenNotFoundError, OSError) as e:
             # Check if it's an auth issue
            error_msg = str(e).lower()
            if "401" in error_msg or "403" in error_msg or "gated" in error_msg or "token" in error_msg:
                print("\n[인증 필요] RMBG-2.0은 사용 승인이 필요한 모델입니다.")
                print("1. Hugging Face 계정으로 로그인 후 라이선스에 동의해주세요: https://huggingface.co/briaai/RMBG-2.0")
                print("2. Access Token을 발급받으세요: https://huggingface.co/settings/tokens")
                print("3. 터미널에서 `huggingface-cli login` 명령어로 로그인하거나 환경변수 `HF_TOKEN`을 설정하세요.")
                print(f"   (또는 모델 파일을 수동으로 {local_model_path} 폴더에 넣어주세요)")
                print("\n[TIP] 인증 없이 즉시 사용을 원하시면 'BiRefNet' 모델을 사용해 보세요.")
                return False
            else:
                 print(f"Error loading model: {e}")
                 print("[TIP] 'BiRefNet' 또는 'InSPyReNet' 모델은 다운로드 즉시 사용 가능합니다.")
                 return False

    model.to(device)
    model.eval()
    
    # Process
    print(f"Processing: {Path(image_path).name}")
    image = Image.open(image_path)
    if image.mode != 'RGB': image = image.convert('RGB')
    orig_size = image.size
    
    # Transform (1024x1024 for RMBG-2.0)
    transform = transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [1.0, 1.0, 1.0])
    ])
    
    input_tensor = transform(image).unsqueeze(0).to(device)
    
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()
    
    pred = preds[0].squeeze()
    pred_pil = transforms.ToPILImage()(pred)
    mask = pred_pil.resize(orig_size, Image.LANCZOS)
    
    image_rgba = image.convert("RGBA")
    image_rgba.putalpha(mask)
    image_rgba.save(output_path, "PNG")
    print(f"✓ Success: {output_path}")
    return True



def remove_background_birefnet_fixed(image_path, output_path):
    """BiRefNet with proper implementation."""
    from torchvision import transforms
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print("Loading BiRefNet model...")
    
    model_id = "ZhengPeng7/BiRefNet"
    try:
        # Check if model exists locally
        model = AutoModelForImageSegmentation.from_pretrained(
            model_id,
            trust_remote_code=True,
            local_files_only=True
        )
    except OSError:
        # Not found locally
        print(f"\n[알림] '{model_id}' 모델을 찾을 수 없습니다.")
        print("최초 1회 다운로드를 시작합니다... (약 170MB)")
        print("잠시만 기다려주세요...\n")
        
        model = AutoModelForImageSegmentation.from_pretrained(
            model_id,
            trust_remote_code=True
        )
    model.to(device)
    model.eval()
    
    # Load and process image
    print(f"Processing: {Path(image_path).name}")
    image = Image.open(image_path)
    
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    orig_size = image.size
    
    # Prepare input
    transform = transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    input_tensor = transform(image).unsqueeze(0).to(device)
    
    # Inference
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()
    
    # Process prediction
    pred = preds[0].squeeze()
    pred_pil = transforms.ToPILImage()(pred)
    mask = pred_pil.resize(orig_size, Image.LANCZOS)
    
    # Apply mask
    image_rgba = image.convert("RGBA")
    image_rgba.putalpha(mask)
    
    # Save
    image_rgba.save(output_path, "PNG")
    print(f"✓ Success: {output_path}")
    
    return True

def remove_background_inspyrenet(image_path, output_path):
    """InSPyReNet - working fallback."""
    try:
        from transparent_background import Remover
    except ImportError:
        print("Installing transparent-background...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'transparent-background'])
        from transparent_background import Remover
    
    print("Loading InSPyReNet model...")
    remover = Remover(mode='base')
    
    print(f"Processing: {Path(image_path).name}")
    image = Image.open(image_path).convert("RGB")
    output = remover.process(image)
    output.save(output_path, "PNG")
    
    print(f"✓ Success: {output_path}")
    return True

def apply_postprocessing(image_rgba, postprocess_type):
    """Apply post-processing to the output image."""
    from PIL import ImageFilter
    
    if postprocess_type == "none":
        return image_rgba
    
    # Get alpha channel
    alpha = image_rgba.split()[-1]
    
    if postprocess_type == "smooth":
        # Edge smoothing - slight blur on alpha
        alpha = alpha.filter(ImageFilter.GaussianBlur(radius=1))
    
    elif postprocess_type == "sharpen":
        # Edge sharpening - unsharp mask on alpha
        alpha = alpha.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
    
    elif postprocess_type == "feather":
        # Matte feathering - more aggressive blur
        alpha = alpha.filter(ImageFilter.GaussianBlur(radius=2))
    
    # Apply processed alpha back
    image_rgba.putalpha(alpha)
    return image_rgba

def apply_background(image_rgba, transparency=True):
    """Apply background based on transparency setting."""
    if transparency:
        return image_rgba
    
    # Create white background
    background = Image.new('RGB', image_rgba.size, (255, 255, 255))
    background.paste(image_rgba, mask=image_rgba.split()[-1])
    return background

def get_unique_path(path: Path) -> Path:
    """
    Returns a unique path by appending a counter if the file already exists.
    E.g., image.png -> image_01.png -> image_02.png
    """
    if not path.exists():
        return path
    
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    
    while True:
        new_name = f"{stem}_{counter:02d}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1

def main():
    parser = argparse.ArgumentParser(description='AI Background Removal (Fixed)')
    parser.add_argument('image_path', help='Input image path')
    parser.add_argument('--output', help='Output path (optional)')
    parser.add_argument('--model', choices=['birefnet', 'inspyrenet', 'rmbg'], 
                       default='rmbg', help='Model to use (default: rmbg)')
    parser.add_argument('--no-transparency', action='store_true', 
                       help='Output with white background instead of transparency')
    parser.add_argument('--postprocess', choices=['none', 'smooth', 'sharpen', 'feather'],
                       default='none', help='Post-processing to apply')
    
    args = parser.parse_args()
    
    image_path = Path(args.image_path)
    if not image_path.exists():
        print(f"Error: Image not found: {image_path}")
        return 1
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = image_path.with_name(f"{image_path.stem}_removed.png")
    
    # Enforce unique path policy
    output_path = get_unique_path(output_path)
    
    try:
        # Select model function
        if args.model == 'birefnet':
            success = remove_background_birefnet_fixed(str(image_path), str(output_path))
        elif args.model == 'inspyrenet':
            success = remove_background_inspyrenet(str(image_path), str(output_path))
        elif args.model == 'rmbg':
            success = remove_background_rmbg(str(image_path), str(output_path))
        else:
            print(f"Error: Unknown model {args.model}")
            return 1
            
        if success:
            # Post-processing
            if args.postprocess != 'none' or args.no_transparency:
                img = Image.open(output_path)
                
                if args.postprocess != 'none':
                    img = apply_postprocessing(img, args.postprocess)
                
                if args.no_transparency:
                    img = apply_background(img, transparency=False)
                
                img.save(output_path, "PNG")
                
            return 0
        else:
            return 1
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
