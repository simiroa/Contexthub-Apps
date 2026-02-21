import torch
import numpy as np
import argparse
from PIL import Image
import sys
import os
from pathlib import Path
import warnings

# Suppress HF warnings
warnings.filtervectors = []
warnings.filterwarnings("ignore")

# Allow large images (disable decompression bomb check)
Image.MAX_IMAGE_PIXELS = None

# Add engine to path to import utils
ENGINE_DIR = Path(__file__).resolve().parents[3]
sys.path.append(str(ENGINE_DIR))
try:
    from utils import paths
except ImportError:
    # Minimal fallback for safety
    class paths:
        RESOURCES_DIR = Path(__file__).resolve().parents[2] / "resources"
        AI_MODELS_DIR = RESOURCES_DIR / "ai_models"
        MARIGOLD_DIR = AI_MODELS_DIR / "marigold"

def main():
    parser = argparse.ArgumentParser(description="Marigold PBR Inference (Expanded)")
    parser.add_argument("input_image", help="Path to input image")
    parser.add_argument("--depth", action="store_true", help="Generate Depth Map")
    parser.add_argument("--normal", action="store_true", help="Generate Normal Map")
    parser.add_argument("--albedo", action="store_true", help="Generate Albedo Map")
    parser.add_argument("--roughness", action="store_true", help="Generate Roughness Map")
    parser.add_argument("--metallicity", action="store_true", help="Generate Metallicity Map")
    parser.add_argument("--orm", action="store_true", help="Generate Packed ORM Map")
    parser.add_argument("--res", type=int, default=768, help="Processing resolution")
    parser.add_argument("--ensemble", type=int, default=1, help="Ensemble size")
    parser.add_argument("--flip_y", action="store_true", help="Flip Normal Y Channel (DirectX style)")
    parser.add_argument("--steps", type=int, default=10, help="Inference steps")
    parser.add_argument("--model_version", type=str, default="v1-1", help="Model version")
    parser.add_argument("--fp16", action="store_true", help="Use Half Precision")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_image)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
        
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if args.fp16 and device == "cuda" else torch.float32
    
    # Lazy Load Heavy Libraries
    import json
    def log_json(status, message, **kwargs):
        print(json.dumps({"status": status, "message": message, **kwargs}), flush=True)

    log_json("initializing", f"Initializing AI Session (Device: {device}, Dtype: {dtype})...")
    
    try:
        from diffusers import MarigoldDepthPipeline, MarigoldNormalsPipeline, MarigoldIntrinsicsPipeline
    except ImportError as e:
        log_json("error", f"Missing 'diffusers' for Marigold. ({e})")
        sys.exit(1)

    # VRAM Awareness
    if device == "cuda":
        total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        if total_vram < 6.0 and args.res > 768:
            log_json("warning", f"Device has {total_vram:.1f}GB VRAM. Reducing resolution to 768 for stability.")
            args.res = 768

    # Load Input
    img = Image.open(input_path)
    
    # Resolution Guard: Prevent OOM on consumer GPUs
    MAX_AI_RES = 2048
    if max(img.size) > MAX_AI_RES:
        print(f"⚠️ Image resolution {img.size} exceeds safety limit ({MAX_AI_RES}). Downscaling for stability.")
        img.thumbnail((MAX_AI_RES, MAX_AI_RES), Image.LANCZOS)
    
    if img.mode != 'RGB': img = img.convert('RGB')
    
    log_json("loading", f"Loading Marigold {args.model_version}...")

    import gc
    def clear_vram():
        if device == "cuda":
            torch.cuda.empty_cache()
        gc.collect()

    try:
        if args.depth:
            log_json("processing", "Generating Depth Map...", task="depth")
            pipe = MarigoldDepthPipeline.from_pretrained(
                f"prs-eth/marigold-depth-{args.model_version}", 
                variant="fp16" if args.fp16 else None, 
                torch_dtype=dtype
            ).to(device)
            
            output = pipe(img, num_inference_steps=args.steps)
            depth_path = input_path.with_name(f"{input_path.stem}_depth.png")
            
            # Depth visualization: relative normalization is standard
            if save_one_file(output.prediction, depth_path, mode="depth"):
                log_json("completed", f"Saved Depth Map", file=depth_path.name, task="depth")
            
            del pipe
            clear_vram()

        if args.normal:
            log_json("processing", "Generating Surface Normals...", task="normal")
            pipe = MarigoldNormalsPipeline.from_pretrained(
                f"prs-eth/marigold-normals-{args.model_version}", 
                variant="fp16" if args.fp16 else None, 
                torch_dtype=dtype
            ).to(device)
            
            output = pipe(img, num_inference_steps=args.steps)
            normal_path = input_path.with_name(f"{input_path.stem}_normal.png")
            
            # Normal map: Absolute [-1, 1] normalization
            if save_one_file(output.prediction, normal_path, mode="normal", flip_y=args.flip_y):
                log_json("completed", f"Saved Normal Map", file=normal_path.name, task="normal")
            
            del pipe
            clear_vram()

        if args.albedo or args.roughness or args.metallicity or args.orm:
            log_json("processing", "Decomposing Material Intrinsics...", task="intrinsics")
            pipe = MarigoldIntrinsicsPipeline.from_pretrained(
                f"prs-eth/marigold-iid-appearance-{args.model_version}", 
                variant="fp16" if args.fp16 else None, 
                torch_dtype=dtype
            ).to(device)
            
            output = pipe(img, num_inference_steps=args.steps)
            
            # Extract prediction map (Shape usually (2, H, W, 3))
            full_pred = output.prediction
            if hasattr(full_pred, 'cpu'): full_pred = full_pred.cpu().numpy()
            
            # Slice results
            # Index 0: Albedo (RGB)
            # Index 1: Material Properties (R=Roughness, G=Metallicity)
            albedo_data = full_pred[0]
            material_data = full_pred[1]

            if args.albedo:
                alb_path = input_path.with_name(f"{input_path.stem}_albedo.png")
                if save_one_file(albedo_data, alb_path, mode="pbr"):
                    log_json("completed", "Saved Albedo Map", file=alb_path.name, task="albedo")
                
            if args.roughness:
                rough_path = input_path.with_name(f"{input_path.stem}_roughness.png")
                if save_one_file(material_data[..., 0], rough_path, mode="pbr"):
                    log_json("completed", "Saved Roughness Map", file=rough_path.name, task="roughness")
                
            if args.metallicity:
                metal_path = input_path.with_name(f"{input_path.stem}_metallicity.png")
                if save_one_file(material_data[..., 1], metal_path, mode="pbr"):
                    log_json("completed", "Saved Metallicity Map", file=metal_path.name, task="metallicity")

            if args.orm:
                orm_path = input_path.with_name(f"{input_path.stem}_orm.png")
                r = material_data[..., 0]
                m = material_data[..., 1]
                o = np.ones_like(r) * 1.0 # Placeholder for Occlusion
                
                # Clip and pack
                def norm(x): return (x - x.min()) / (x.max() - x.min() + 1e-8)
                orm = np.stack([norm(o), norm(r), norm(m)], axis=-1)
                Image.fromarray((orm * 255).astype(np.uint8)).save(orm_path)
                log_json("completed", "Saved Packed ORM Map", file=orm_path.name, task="orm")

            del pipe
            clear_vram()

        if device == "cuda":
            torch.cuda.empty_cache()
            
    except Exception as e:
        import traceback
        print(f"Inference Error: {e}")
        traceback.print_exc()
        return 1

    return 0

def save_one_file(data, path, mode="pbr", flip_y=False):
    """Save map with context-aware normalization."""
    if data is None: return False
    try:
        if isinstance(data, (list, tuple)): data = data[0]
        if hasattr(data, 'cpu'): data = data.cpu().numpy()
        data = np.squeeze(data)
        
        # Ensure (H, W, C) layout
        if data.ndim > 2 and data.shape[0] <= 4:
            data = np.transpose(data, (1, 2, 0))
            
        if data.dtype == np.float32 or data.dtype == np.float16:
            if mode == "normal":
                # Standard Normal mapping: [-1, 1] -> [0, 1]
                # Marigold normals are (X, Y, Z) in cam space
                if flip_y:
                    data[..., 1] = -data[..., 1]
                
                # Map to [0, 1]
                data = (data + 1.0) / 2.0
                data = np.clip(data * 255, 0, 255).astype(np.uint8)
            elif mode == "depth":
                # Depth preview: relative normalization is best for visualization
                d_min, d_max = data.min(), data.max()
                data = (data - d_min) / (d_max - d_min + 1e-8)
                data = (data * 255).astype(np.uint8)
            else:
                # Albedo/Roughness/Metal: assume [0, 1] range
                # Use absolute clipping to protect colors
                data = np.clip(data * 255, 0, 255).astype(np.uint8)
            
        Image.fromarray(data).save(path)
        return True
    except Exception as e:
        print(f"Save error for {path}: {e}")
        return False

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
