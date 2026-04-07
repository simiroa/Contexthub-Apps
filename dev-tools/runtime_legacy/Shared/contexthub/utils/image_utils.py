import sys
from pathlib import Path
from PIL import Image

# Add src to path if needed (though usually imported from scripts)
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from .explorer import get_selection_from_explorer

def scan_for_images(target=None, recursive=False):
    """
    Scans for images based on a target path (file or directory) or selection.
    
    Args:
        target: str or Path, or list of strings/Paths. The starting point.
        recursive: bool, whether to scan directories recursively (default False for safety).
        
    Returns:
        tuple(list[Path], int): (List of valid image Paths, Count of total candidates checked)
    """
    candidates = set()
    
    # 1. Normalize Input
    if target:
        if isinstance(target, (list, tuple)):
            for t in target:
                candidates.add(Path(t))
        else:
            p = Path(target)
            candidates.add(p)
            # Try to get explorer selection if it matches target context
            try:
                # Only check explorer if target looks like a path passed from context menu
                sel = get_selection_from_explorer(str(p))
                if sel:
                    for s in sel: candidates.add(Path(s))
            except:
                pass
    
    valid_files = []
    # Extensions to fast-accept without opening
    # DDS added for input support (Pillow can read, but not write DDS)
    valid_exts = {
        # Standard
        '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp', '.tga', '.ico', '.jfif', 
        # Modern
        '.heic', '.avif', 
        # Vector/PDF (converted to raster)
        '.ai', '.svg', '.pdf', '.eps', 
        # HDR/Pro
        '.exr', '.hdr', '.psd', '.psb', '.dds', 
        # RAW
        '.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2', '.sr2', '.raf', '.cr3', '.srw', '.pef', '.erf', '.mos', '.mrw', '.kdc', '.3fr', '.fff', '.iiq'
    }
    
    checked_count = 0
    
    # Process candidates
    initial_candidates = list(candidates)
    processed_paths = set()
    ignored_paths = [] # Keep track of files skipped by extension check
    
    for p in initial_candidates:
        if not p.exists(): continue
        
        if p.is_dir():
            # Expand Directory
            # Use iterdir() for non-recursive or rglob defined by recursive flag
            try:
                iterator = p.rglob('*') if recursive else p.iterdir()
                for f in iterator:
                    if f.is_file():
                        processed_paths.add(f)
                        if f.suffix.lower() in valid_exts:
                            valid_files.append(f)
                        else:
                            ignored_paths.append(f)
            except Exception as e:
                pass # Permission error etc
                
        else:
            processed_paths.add(p)
            checked_count += 1
            # File Check
            # 1. Fast Check
            if p.suffix.lower() in valid_exts:
                valid_files.append(p)
            else:
                # 2. Deep Check (PIL) for files without standard extensions
                try:
                    with Image.open(p) as img:
                        img.verify()
                    valid_files.append(p)
                except:
                    pass
    
    return sorted(list(set(valid_files))), len(processed_paths)

def load_image_unified(path: Path) -> Image.Image:
    """
    Unified Image Loader for all supported formats.
    Returns: PIL.Image (RGB/RGBA mode) or raises Exception.
    """
    suffix = path.suffix.lower()
    
    # 1. PDF / AI (PDF-based)
    if suffix in ['.ai', '.pdf']:
        from pdf2image import convert_from_path
        # Convert first page only
        images = convert_from_path(str(path), first_page=1, last_page=1)
        if images:
            return images[0]
        else:
            raise ValueError("No image data found in PDF/AI")

    # 2. SVG
    elif suffix == '.svg':
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        import io
        
        drawing = svg2rlg(str(path))
        img_data = io.BytesIO()
        renderPM.drawToFile(drawing, img_data, fmt="PNG")
        img_data.seek(0)
        return Image.open(img_data)

    # 3. HEIC / AVIF
    elif suffix in ['.heic', '.avif']:
        from pillow_heif import register_heif_opener
        register_heif_opener() # This registers the plugin globally for this session
        img = Image.open(path)
        img.load() # Ensure loaded
        return img
        
    # 4. RAW Formats
    elif suffix in ['.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2', '.sr2', '.raf', '.cr3', '.srw', '.pef', '.erf', '.mos', '.mrw', '.kdc', '.3fr', '.fff', '.iiq']:
        import rawpy
        with rawpy.imread(str(path)) as raw:
            rgb = raw.postprocess() # Demosaic to RGB numpy array
            return Image.fromarray(rgb)

    # 5. HDR / EXR
    elif suffix in ['.hdr', '.exr']:
        import imageio
        import numpy as np
        
        # Load with ImageIO
        # imageio.imread returns numpy array
        # Try to force a freeimage or compatible plugin if default fails?
        # Usually imageio auto-detects.
        try:
             img_data = imageio.imread(str(path), format='EXR' if suffix == '.exr' else 'HDR-FI')
        except:
             img_data = imageio.imread(str(path))

        if img_data is None:
            raise ValueError("Failed to load HDR/EXR data")
        
        # Tonemap Logic (Basic Gamma)
        img_data = np.nan_to_num(img_data)
        
        if img_data.dtype.kind == 'f':
            img_data = np.clip(img_data, 0, None)
            # Simple Exposure / normalization to 1.0? 
            # Or just clip 1.0? Let's clip to 1.0 for consistency with standard viewers
            img_data = np.clip(img_data, 0.0, 1.0)
            img_data = np.power(img_data, 1/2.2) # Gamma
            img_data = (img_data * 255).astype(np.uint8)
            
        return Image.fromarray(img_data)

    # 6. Standard & Pillow Native (PSD, DDS, TGA, BMP, JPG, PNG, WEBP, etc.)
    else:
        # Pillow handles PSD, DDS, TGA naturally
        img = Image.open(path)
        
        # Handle specific quirks
        # PSD: Pillow usually loads combined image.
        if suffix == '.psd':
             img.load() # Force load
        
        return img
