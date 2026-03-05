"""
VTracer Wrapper - High-performance image to SVG vectorization.
Uses Rust-based vtracer for fast and accurate path tracing.
"""
# import vtracer # Moved to lazy loading in vectorize_image
from pathlib import Path
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import io

# Default VTracer settings optimized for character rigging
DEFAULT_CONFIG = {
    "colormode": "color",        # Full color output
    "hierarchical": "stacked",   # Overlapping paths for seamless rigging
    "mode": "spline",            # Smooth bezier curves
    "filter_speckle": 4,         # Remove noise smaller than 4px
    "color_precision": 6,        # Color grouping precision
    "layer_difference": 16,      # Color layer separation threshold
    "corner_threshold": 60,      # Corner vs curve detection
    "length_threshold": 4.0,     # Minimum path segment length
    "max_iterations": 10,        # Optimization iterations
    "splice_threshold": 45,      # Curve splice angle
    "path_precision": 3,         # SVG path decimal precision
}


def vectorize_image(
    image_path: Path,
    output_path: Path = None,
    config: dict = None
) -> str:
    """
    Convert a raster image to SVG using vtracer.
    
    Args:
        image_path: Path to input image (PNG with alpha recommended)
        output_path: Optional path to save SVG file
        config: Optional vtracer configuration override
    
    Returns:
        SVG content as string
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    
    # Read image bytes
    img_path = Path(image_path)
    
    # Ensure PNG format for best alpha handling
    with Image.open(img_path) as img:
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Save to bytes buffer
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
    
    # Run vtracer
    import vtracer
    svg_str = vtracer.convert_raw_image_to_svg(
        img_bytes,
        img_format='png',
        colormode=cfg['colormode'],
        hierarchical=cfg['hierarchical'],
        mode=cfg['mode'],
        filter_speckle=cfg['filter_speckle'],
        color_precision=cfg['color_precision'],
        layer_difference=cfg['layer_difference'],
        corner_threshold=cfg['corner_threshold'],
        length_threshold=cfg['length_threshold'],
        max_iterations=cfg['max_iterations'],
        splice_threshold=cfg['splice_threshold'],
        path_precision=cfg['path_precision'],
    )
    
    # Optionally save to file
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(svg_str, encoding='utf-8')
    
    return svg_str


def _vectorize_single(args):
    """Worker function for parallel processing."""
    img_path, out_path, config = args
    try:
        svg = vectorize_image(img_path, out_path, config)
        return (img_path, True, None)
    except Exception as e:
        return (img_path, False, str(e))


def vectorize_batch(
    image_paths: list,
    output_dir: Path,
    config: dict = None,
    max_workers: int = None,
    progress_callback=None
) -> list:
    """
    Vectorize multiple images in parallel using multiprocessing.
    
    Args:
        image_paths: List of image paths to process
        output_dir: Directory to save SVG files
        config: Optional vtracer configuration
        max_workers: Number of parallel workers (defaults to CPU count - 1)
        progress_callback: Optional callback(current, total) for progress updates
    
    Returns:
        List of (path, success, error) tuples
    """
    if max_workers is None:
        max_workers = max(1, multiprocessing.cpu_count() - 1)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Prepare arguments
    args_list = []
    for img_path in image_paths:
        p = Path(img_path)
        out_path = output_dir / f"{p.stem}.svg"
        args_list.append((p, out_path, config))
    
    results = []
    total = len(args_list)
    
    # Use ProcessPoolExecutor for true parallelism
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for i, result in enumerate(executor.map(_vectorize_single, args_list)):
            results.append(result)
            if progress_callback:
                progress_callback(i + 1, total)
    
    return results


if __name__ == "__main__":
    # Simple test
    import sys
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.exists():
            svg = vectorize_image(p)
            print(f"Generated SVG: {len(svg)} bytes")
            out = p.with_suffix('.svg')
            out.write_text(svg, encoding='utf-8')
            print(f"Saved to: {out}")
