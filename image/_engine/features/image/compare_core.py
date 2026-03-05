"""
Image Compare Core - Image loading, diff calculation, SSIM
"""
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image

# Optional imports
# Heavy imports moved to lazy loading in functions
# import cv2
# import OpenEXR
# import Imath



def load_image(path: str, channel: str = "RGB") -> Optional[np.ndarray]:
    """
    Load image and return as numpy array.
    Supports: PNG, JPG, EXR, TGA, TIFF, BMP
    
    Args:
        path: Image file path
        channel: Channel to extract ("RGB", "R", "G", "B", "A", or EXR channel name)
    
    Returns:
        numpy array (H, W, C) normalized to 0-1 range
    """
    path = Path(path)
    ext = path.suffix.lower()
    
    if ext == ".exr":
        return _load_exr(path, channel)
    else:
        import numpy as np
        return _load_standard(path, channel)


def _load_standard(path: Path, channel: str) -> Optional[np.ndarray]:
    """Load standard image formats via Pillow."""
    try:
        img = Image.open(path)
        
        # Convert to RGBA if has alpha
        if img.mode == "RGBA":
            arr = np.array(img).astype(np.float32) / 255.0
        elif img.mode == "RGB":
            arr = np.array(img).astype(np.float32) / 255.0
        elif img.mode in ("L", "P"):
            img = img.convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
        else:
            img = img.convert("RGBA")
            arr = np.array(img).astype(np.float32) / 255.0
        
        # Extract channel
        if channel == "RGB":
            return arr[:, :, :3] if arr.shape[2] >= 3 else arr
        elif channel == "R":
            return arr[:, :, 0:1]
        elif channel == "G":
            return arr[:, :, 1:2]
        elif channel == "B":
            return arr[:, :, 2:3]
        elif channel == "A":
            if arr.shape[2] >= 4:
                return arr[:, :, 3:4]
            return np.ones((arr.shape[0], arr.shape[1], 1), dtype=np.float32)
        else:
            return arr[:, :, :3]
            
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None


def _load_exr(path: Path, channel: str):
    """Load EXR image with channel selection."""
    try:
        import OpenEXR
        import Imath
        import numpy as np
    except ImportError:
        return None
    
    try:
        exr = OpenEXR.InputFile(str(path))
        header = exr.header()
        dw = header['dataWindow']
        width = dw.max.x - dw.min.x + 1
        height = dw.max.y - dw.min.y + 1
        
        channels = header['channels'].keys()
        pt = Imath.PixelType(Imath.PixelType.FLOAT)
        
        def read_channel(name: str) -> np.ndarray:
            data = exr.channel(name, pt)
            return np.frombuffer(data, dtype=np.float32).reshape(height, width)
        
        if channel == "RGB":
            # Try standard RGB channels
            r_name = next((c for c in channels if c in ("R", "r")), None)
            g_name = next((c for c in channels if c in ("G", "g")), None)
            b_name = next((c for c in channels if c in ("B", "b")), None)
            
            if r_name and g_name and b_name:
                r = read_channel(r_name)
                g = read_channel(g_name)
                b = read_channel(b_name)
                return np.stack([r, g, b], axis=-1)
        
        elif channel in channels:
            # Direct channel access
            return read_channel(channel)[:, :, np.newaxis]
        
        elif channel in ("R", "G", "B", "A"):
            name = next((c for c in channels if c.upper() == channel), None)
            if name:
                return read_channel(name)[:, :, np.newaxis]
        
        # Fallback: first 3 channels
        ch_list = list(channels)[:3]
        arrs = [read_channel(c) for c in ch_list]
        return np.stack(arrs, axis=-1)
        
    except Exception as e:
        print(f"Error loading EXR {path}: {e}")
        return None


def get_exr_channels(path: str) -> List[str]:
    """Get list of available channels in EXR file."""
    try:
        import OpenEXR
    except ImportError:
        return []
    
    try:
        exr = OpenEXR.InputFile(str(path))
        return list(exr.header()['channels'].keys())
    except:
        return []


def compute_diff(img_a, img_b):
    import numpy as np
    """
    Compute absolute difference between two images.
    
    Returns:
        diff_image: Difference visualization (red = different)
        diff_count: Number of different pixels
    """
    # Ensure same size
    if img_a.shape != img_b.shape:
        # Resize B to match A
        h, w = img_a.shape[:2]
        img_b = _resize_array(img_b, w, h)
    
    # Calculate absolute difference
    diff = np.abs(img_a - img_b)
    
    # Count different pixels (threshold 0.01)
    diff_mask = np.max(diff, axis=-1) > 0.01
    diff_count = int(np.sum(diff_mask))
    
    # Create visualization: red overlay on differences
    diff_vis = np.zeros_like(img_a)
    diff_vis[:, :, 0] = np.max(diff, axis=-1)  # Red channel = diff intensity
    
    return diff_vis, diff_count


def compute_ssim(img_a, img_b) -> float:
    import numpy as np
    """
    Compute SSIM (Structural Similarity Index) between two images.
    
    Returns:
        SSIM score (0.0 to 1.0, 1.0 = identical)
    """
    try:
        from skimage.metrics import structural_similarity as ssim
        
        # Ensure same size
        if img_a.shape != img_b.shape:
            h, w = img_a.shape[:2]
            img_b = _resize_array(img_b, w, h)
        
        # Convert to grayscale for SSIM
        if len(img_a.shape) == 3 and img_a.shape[2] >= 3:
            gray_a = 0.299 * img_a[:,:,0] + 0.587 * img_a[:,:,1] + 0.114 * img_a[:,:,2]
            gray_b = 0.299 * img_b[:,:,0] + 0.587 * img_b[:,:,1] + 0.114 * img_b[:,:,2]
        else:
            gray_a = img_a[:,:,0] if len(img_a.shape) == 3 else img_a
            gray_b = img_b[:,:,0] if len(img_b.shape) == 3 else img_b
        
        return ssim(gray_a, gray_b, data_range=1.0)
        
    except ImportError:
        # Fallback: simple MSE-based similarity
        mse = np.mean((img_a - img_b) ** 2)
        return max(0.0, 1.0 - mse * 10)


def _resize_array(arr, width: int, height: int):
    """Resize numpy array to target size."""
    try:
        import cv2
        return cv2.resize(arr, (width, height), interpolation=cv2.INTER_LINEAR)
    except ImportError:
        import numpy as np
        # Pillow fallback
        img = Image.fromarray((arr * 255).astype(np.uint8))
        img = img.resize((width, height), Image.LANCZOS)
        return np.array(img).astype(np.float32) / 255.0


def array_to_pil(arr) -> Image.Image:
    import numpy as np
    """Convert numpy array (0-1 range) to PIL Image."""
    # Clamp and convert
    arr = np.clip(arr, 0, 1)
    arr = (arr * 255).astype(np.uint8)
    
    if len(arr.shape) == 2:
        return Image.fromarray(arr, mode='L')
    elif arr.shape[2] == 1:
        return Image.fromarray(arr[:, :, 0], mode='L')
    elif arr.shape[2] == 3:
        return Image.fromarray(arr, mode='RGB')
    elif arr.shape[2] == 4:
        return Image.fromarray(arr, mode='RGBA')
    else:
        return Image.fromarray(arr[:, :, :3], mode='RGB')


def create_side_by_side(img_a, img_b, 
                        diff=None) -> Image.Image:
    import numpy as np
    """Create side-by-side comparison image."""
    # Ensure same height
    h = max(img_a.shape[0], img_b.shape[0])
    w_a, w_b = img_a.shape[1], img_b.shape[1]
    
    if diff is not None:
        total_w = w_a + w_b + diff.shape[1]
        result = np.zeros((h, total_w, 3), dtype=np.float32)
        result[:img_a.shape[0], :w_a] = img_a[:, :, :3]
        result[:img_b.shape[0], w_a:w_a+w_b] = img_b[:, :, :3]
        result[:diff.shape[0], w_a+w_b:] = diff[:, :, :3]
    else:
        total_w = w_a + w_b
        result = np.zeros((h, total_w, 3), dtype=np.float32)
        result[:img_a.shape[0], :w_a] = img_a[:, :, :3]
        result[:img_b.shape[0], w_a:] = img_b[:, :, :3]
    
    return array_to_pil(result)
