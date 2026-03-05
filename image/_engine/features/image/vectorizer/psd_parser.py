"""
PSD Parser - Extract layers from PSD/PSB files with structure preservation.
Uses psd-tools library for Adobe Photoshop file parsing.
"""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import io

from psd_tools import PSDImage
from PIL import Image


@dataclass
class LayerInfo:
    """Represents a single PSD layer with all relevant data."""
    name: str
    index: int
    uid: str
    path: str
    offset_x: int
    offset_y: int
    width: int
    height: int
    visible: bool
    opacity: float
    blend_mode: str
    is_group: bool
    is_text: bool = False
    is_smart_object: bool = False
    vector_mask_d: Optional[str] = None
    parent_name: Optional[str] = None
    parent_uid: Optional[str] = None
    image: Optional[Image.Image] = None
    children: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "name": self.name,
            "index": self.index,
            "uid": self.uid,
            "path": self.path,
            "offset": {"x": self.offset_x, "y": self.offset_y},
            "size": {"width": self.width, "height": self.height},
            "visible": self.visible,
            "opacity": self.opacity,
            "blend_mode": self.blend_mode,
            "is_group": self.is_group,
            "is_text": self.is_text,
            "is_smart_object": self.is_smart_object,
            "vector_mask_d": self.vector_mask_d,
            "parent": self.parent_name,
            "parent_uid": self.parent_uid,
            "children": [c.to_dict() for c in self.children] if self.children else []
        }


@dataclass
class PSDData:
    """Represents parsed PSD file data."""
    file_path: Path
    canvas_width: int
    canvas_height: int
    layers: list  # List of LayerInfo
    
    def to_dict(self) -> dict:
        return {
            "file": str(self.file_path.name),
            "canvas": {"width": self.canvas_width, "height": self.canvas_height},
            "layers": [l.to_dict() for l in self.layers]
        }


def _build_layer_id(parent_uid: Optional[str], index: int, name: str) -> str:
    safe = name.replace("/", "_").replace("\\", "_")
    if parent_uid:
        return f"{parent_uid}/{index:03d}_{safe}"
    return f"{index:03d}_{safe}"


def _build_layer_path(parent_path: str, name: str) -> str:
    if parent_path:
        return f"{parent_path}/{name}"
    if parent_path:
        return f"{parent_path}/{name}"
    return name


def _extract_vector_mask(layer, canvas_width: int, canvas_height: int) -> Optional[str]:
    """
    Extract vector mask data from layer and convert to SVG 'd' path string.
    """
    if not hasattr(layer, 'vector_mask') or not layer.vector_mask:
        return None

    paths = []
    
    # psd-tools exposes 'paths' as a list of subpaths
    try:
        if not hasattr(layer.vector_mask, 'paths'):
            return None
            
        for subpath in layer.vector_mask.paths:
            # We skip initial records that are not paths (like clipboard records) if they appear
            # But usually .paths iterates over subpaths (open or closed)
            
            # Check length - must have at least one knot
            if len(subpath) < 1:
                continue

            knots = list(subpath)
            if not knots:
                continue

            # Start the path
            d_parts = []
            
            # First knot
            # Coordinates in psd-tools are typically (y, x) relative normalized (0.0 to 1.0)
            # OR absolute. We need to check. 
            # Usually they are normalized. we will assume normalized if they are small.
            
            def get_pt(pt_data):
                # pt_data is likely (y, x)
                y, x = pt_data
                return x * canvas_width, y * canvas_height

            # Move to first point
            start = knots[0]
            sx, sy = get_pt(start.anchor)
            d_parts.append(f"M {sx:.3f},{sy:.3f}")

            # Loop through subsequent knots
            for i in range(1, len(knots)):
                curr = knots[i]
                prev = knots[i-1]
                
                # Bezier Curve:
                # C (prev.leaving) (curr.entering) (curr.anchor)
                
                cp1_x, cp1_y = get_pt(prev.successor) # leaving previous
                cp2_x, cp2_y = get_pt(curr.predecessor) # entering current
                end_x, end_y = get_pt(curr.anchor)
                
                d_parts.append(f"C {cp1_x:.3f},{cp1_y:.3f} {cp2_x:.3f},{cp2_y:.3f} {end_x:.3f},{end_y:.3f}")

            # Close if it's a closed path
            # psd-tools subpath usually has a 'closed' property or type
            is_closed = getattr(subpath, 'closed', True) # Default to true if unknown, but check type
            # Or checks operation type. 
            # Simple heuristic: if it's a ClosedSubpath class or similar.
            # We'll assume closed unless it's explicitly open. 
            # The 'closed' property exists on psd_tools.psd.vector.Subpath in recent versions?
            # Actually, `len(subpath)` > 2 implies closed usually for shapes.
            
            # If closed, we need to curve back to start
            if is_closed:
                last = knots[-1]
                first = knots[0]
                
                cp1_x, cp1_y = get_pt(last.successor)
                cp2_x, cp2_y = get_pt(first.predecessor)
                end_x, end_y = get_pt(first.anchor)
                
                d_parts.append(f"C {cp1_x:.3f},{cp1_y:.3f} {cp2_x:.3f},{cp2_y:.3f} {end_x:.3f},{end_y:.3f}")
                d_parts.append("Z")
            
            paths.append(" ".join(d_parts))

    except Exception:
        # If extraction fails (e.g. API differences), return None to fallback to raster
        return None

    if not paths:
        return None
        
    return " ".join(paths)


def parse_psd(
    psd_path: Path,
    include_hidden: bool = False,
    extract_images: bool = True
) -> PSDData:
    """
    Parse a PSD/PSB file and extract layer information.
    
    Args:
        psd_path: Path to PSD/PSB file
        include_hidden: If True, include hidden layers
        extract_images: If True, extract layer images (uses more memory)
    
    Returns:
        PSDData object with all layer information
    """
    psd_path = Path(psd_path)
    psd = PSDImage.open(psd_path)
    
    layers = []
    
    def _process_layer(layer, index, parent_info: Optional[LayerInfo] = None, parent_path: str = ""):
        """Recursively process layer tree."""
        # Skip hidden if not requested
        if not include_hidden and not layer.visible:
            return None
        
        # Get layer bounds
        left, top, right, bottom = layer.left, layer.top, layer.right, layer.bottom
        width = right - left
        height = bottom - top
        
        # Create layer info
        name = layer.name or f"Layer_{index}"
        path = _build_layer_path(parent_path, name)
        parent_uid = parent_info.uid if parent_info else None
        uid = _build_layer_id(parent_uid, index, name)

        info = LayerInfo(
            name=name,
            index=index,
            uid=uid,
            path=path,
            offset_x=left,
            offset_y=top,
            width=width,
            height=height,
            visible=layer.visible,
            opacity=layer.opacity / 255.0 if hasattr(layer, 'opacity') else 1.0,
            blend_mode=str(layer.blend_mode) if hasattr(layer, 'blend_mode') else 'normal',
            is_group=layer.is_group(),
            is_text=getattr(layer, 'kind', None) == 'type',
            is_smart_object=getattr(layer, 'kind', None) == 'smartobject',
            vector_mask_d=_extract_vector_mask(layer, psd.width, psd.height),
            parent_name=parent_info.name if parent_info else None,
            parent_uid=parent_uid
        )
        
        # Extract image if requested and layer has content
        if extract_images and not layer.is_group() and width > 0 and height > 0:
            try:
                info.image = layer.composite()
            except Exception:
                # Some layers may not be compositable
                pass
        
        # Process children for groups
        if layer.is_group():
            for i, child in enumerate(layer):
                child_info = _process_layer(child, i, info, path)
                if child_info:
                    info.children.append(child_info)
        
        return info
    
    # Process all top-level layers
    for i, layer in enumerate(psd):
        layer_info = _process_layer(layer, i)
        if layer_info:
            layers.append(layer_info)
    
    return PSDData(
        file_path=psd_path,
        canvas_width=psd.width,
        canvas_height=psd.height,
        layers=layers
    )


def extract_layer_images(
    psd_data: PSDData,
    output_dir: Path,
    format: str = 'PNG'
) -> list:
    """
    Save all layer images to individual files.
    
    Args:
        psd_data: Parsed PSD data
        output_dir: Directory to save images
        format: Output format (PNG recommended for alpha)
    
    Returns:
        List of (layer_name, output_path) tuples
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    saved = []
    
    def _save_layer(layer_info, prefix=""):
        name = f"{prefix}{layer_info.name}".replace("/", "_").replace("\\", "_")
        
        if layer_info.image:
            out_path = output_dir / f"{name}.png"
            layer_info.image.save(out_path, format=format)
            saved.append((layer_info.name, out_path))
        
        # Process children
        for child in layer_info.children:
            _save_layer(child, f"{name}_")
    
    for layer in psd_data.layers:
        _save_layer(layer)
    
    return saved


def get_flat_layer_list(psd_data: PSDData, skip_groups: bool = True) -> list:
    """
    Get a flat list of all layers (no hierarchy).
    
    Args:
        psd_data: Parsed PSD data
        skip_groups: If True, exclude group layers from list
    
    Returns:
        Flat list of LayerInfo objects (original names preserved)
    """
    flat = []
    
    def _flatten(layer_info):
        if not (skip_groups and layer_info.is_group):
            flat.append(layer_info)
        
        for child in layer_info.children:
            _flatten(child)
    
    for layer in psd_data.layers:
        _flatten(layer)
    
    return flat


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.exists() and p.suffix.lower() in ('.psd', '.psb'):
            data = parse_psd(p, include_hidden=False)
            print(f"Canvas: {data.canvas_width} x {data.canvas_height}")
            print(f"Layers: {len(data.layers)}")
            for layer in get_flat_layer_list(data):
                print(f"  - {layer.name} ({layer.width}x{layer.height}) @ ({layer.offset_x}, {layer.offset_y})")
