"""
SVG Builder - Combine vectorized layers into structured SVG with metadata.
Generates integrated output files for After Effects rigging workflows.
"""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Iterable
import json
import math
import re
import xml.etree.ElementTree as ET


@dataclass
class SvgPath:
    """Represents a single SVG path with a resolved transform."""
    d: str
    fill: str
    style: str
    transform: Tuple[float, float, float, float, float, float]
    opacity: float = 1.0


@dataclass
class LayerSVG:
    """Represents a layer or group in the vectorized output."""
    name: str
    uid: str
    path: str
    offset_x: float
    offset_y: float
    width: float
    height: float
    anchor_x: Optional[float]
    anchor_y: Optional[float]
    is_group: bool = False
    duik_name: Optional[str] = None
    parent_uid: Optional[str] = None
    svg_paths: List[SvgPath] = field(default_factory=list)
    children: List["LayerSVG"] = field(default_factory=list)


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-:.]+", "_", value)


def _parse_length(value: Optional[str]) -> float:
    if not value:
        return 0.0
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        match = re.match(r"([-+]?\d*\.?\d+)", value)
        return float(match.group(1)) if match else 0.0


def _parse_viewbox(value: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not value:
        return None
    parts = [p for p in re.split(r"[,\s]+", value.strip()) if p]
    if len(parts) != 4:
        return None
    try:
        return tuple(float(p) for p in parts)
    except ValueError:
        return None


def _identity_matrix() -> Tuple[float, float, float, float, float, float]:
    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _translate_matrix(tx: float, ty: float) -> Tuple[float, float, float, float, float, float]:
    return (1.0, 0.0, 0.0, 1.0, tx, ty)


def _scale_matrix(sx: float, sy: float) -> Tuple[float, float, float, float, float, float]:
    return (sx, 0.0, 0.0, sy, 0.0, 0.0)


def _rotate_matrix(angle_deg: float) -> Tuple[float, float, float, float, float, float]:
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return (cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)


def _skewx_matrix(angle_deg: float) -> Tuple[float, float, float, float, float, float]:
    rad = math.radians(angle_deg)
    return (1.0, 0.0, math.tan(rad), 1.0, 0.0, 0.0)


def _skewy_matrix(angle_deg: float) -> Tuple[float, float, float, float, float, float]:
    rad = math.radians(angle_deg)
    return (1.0, math.tan(rad), 0.0, 1.0, 0.0, 0.0)


def _multiply_matrix(
    m1: Tuple[float, float, float, float, float, float],
    m2: Tuple[float, float, float, float, float, float]
) -> Tuple[float, float, float, float, float, float]:
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply_matrix(
    m: Tuple[float, float, float, float, float, float],
    x: float,
    y: float
) -> Tuple[float, float]:
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def _apply_linear(
    m: Tuple[float, float, float, float, float, float],
    x: float,
    y: float
) -> Tuple[float, float]:
    a, b, c, d, _, _ = m
    return (a * x + c * y, b * x + d * y)


def _matrix_is_identity(m: Tuple[float, float, float, float, float, float], eps: float = 1e-9) -> bool:
    a, b, c, d, e, f = m
    return (
        abs(a - 1.0) < eps and abs(d - 1.0) < eps and
        abs(b) < eps and abs(c) < eps and abs(e) < eps and abs(f) < eps
    )


_TRANSFORM_RE = re.compile(r"([A-Za-z]+)\s*\(([^)]*)\)")


def _parse_transform(transform_str: Optional[str]) -> Tuple[float, float, float, float, float, float]:
    if not transform_str:
        return _identity_matrix()

    matrix = _identity_matrix()

    for name, params_str in _TRANSFORM_RE.findall(transform_str):
        name = name.strip().lower()
        params = [p for p in re.split(r"[,\s]+", params_str.strip()) if p]
        try:
            nums = [float(p) for p in params]
        except ValueError:
            nums = []

        if name == "translate":
            tx = nums[0] if len(nums) >= 1 else 0.0
            ty = nums[1] if len(nums) >= 2 else 0.0
            t = _translate_matrix(tx, ty)
        elif name == "scale":
            sx = nums[0] if len(nums) >= 1 else 1.0
            sy = nums[1] if len(nums) >= 2 else sx
            t = _scale_matrix(sx, sy)
        elif name == "rotate":
            angle = nums[0] if len(nums) >= 1 else 0.0
            t = _rotate_matrix(angle)
            if len(nums) >= 3:
                cx, cy = nums[1], nums[2]
                t = _multiply_matrix(_translate_matrix(cx, cy), _multiply_matrix(t, _translate_matrix(-cx, -cy)))
        elif name == "skewx":
            angle = nums[0] if len(nums) >= 1 else 0.0
            t = _skewx_matrix(angle)
        elif name == "skewy":
            angle = nums[0] if len(nums) >= 1 else 0.0
            t = _skewy_matrix(angle)
        elif name == "matrix" and len(nums) == 6:
            t = (nums[0], nums[1], nums[2], nums[3], nums[4], nums[5])
        else:
            continue

        # Apply transforms in listed order (pre-multiply)
        matrix = _multiply_matrix(t, matrix)

    return matrix


def _extract_fill(elem: ET.Element) -> str:
    fill = elem.get("fill")
    if fill and fill != "none":
        return fill

    style = elem.get("style", "")
    match = re.search(r"fill\s*:\s*([^;]+)", style)
    if match:
        value = match.group(1).strip()
        if value != "none":
            return value

    return "#000000"


def _extract_opacity(elem: ET.Element) -> float:
    # 1. Global opacity
    opacity = 1.0
    op_attr = elem.get("opacity")
    if op_attr:
        try:
            opacity = float(op_attr)
        except ValueError:
            pass
    else:
        style = elem.get("style", "")
        # Look for 'opacity' but ensure it's not 'fill-opacity' or 'stroke-opacity'
        # A simple way is to ensure it starts with 'opacity' or follows a semicolon and whitespace
        match = re.search(r"(?:^|;)\s*opacity\s*:\s*([\d.]+)", style)
        if match:
            try:
                opacity = float(match.group(1))
            except ValueError:
                pass

    # 2. Fill opacity
    fill_opacity = 1.0
    fill_op_attr = elem.get("fill-opacity")
    if fill_op_attr:
        try:
            fill_opacity = float(fill_op_attr)
        except ValueError:
            pass
    else:
        style = elem.get("style", "")
        match = re.search(r"(?:^|;)\s*fill-opacity\s*:\s*([\d.]+)", style)
        if match:
            try:
                fill_opacity = float(match.group(1))
            except ValueError:
                pass

    return opacity * fill_opacity


def _is_path(elem: ET.Element) -> bool:
    return elem.tag.lower().endswith("path")


def _walk_svg_paths(elem: ET.Element, parent_matrix: Tuple[float, float, float, float, float, float], out_paths: List[SvgPath]) -> None:
    local_matrix = parent_matrix
    transform_attr = elem.get("transform")
    if transform_attr:
        local_matrix = _multiply_matrix(parent_matrix, _parse_transform(transform_attr))

    if _is_path(elem):
        d = elem.get("d", "")
        style = elem.get("style", "")
        fill = _extract_fill(elem)
        opacity = _extract_opacity(elem)
        out_paths.append(SvgPath(d=d, fill=fill, style=style, transform=local_matrix, opacity=opacity))

    for child in list(elem):
        _walk_svg_paths(child, local_matrix, out_paths)


def parse_svg_document(
    svg_content: str,
    target_width: Optional[float] = None,
    target_height: Optional[float] = None
) -> Tuple[List[SvgPath], float, float]:
    """
    Parse SVG content into a list of SvgPath objects with resolved transforms.
    Returns: (paths, width, height)
    """
    root = ET.fromstring(svg_content)

    width = _parse_length(root.get("width"))
    height = _parse_length(root.get("height"))

    viewbox = _parse_viewbox(root.get("viewBox"))
    if viewbox is None:
        viewbox = (0.0, 0.0, width, height)

    vb_min_x, vb_min_y, vb_w, vb_h = viewbox
    if width <= 0.0:
        width = vb_w
    if height <= 0.0:
        height = vb_h
    if target_width is not None:
        width = float(target_width)
    if target_height is not None:
        height = float(target_height)

    if vb_w == 0.0 or vb_h == 0.0:
        doc_transform = _identity_matrix()
    else:
        scale_x = width / vb_w
        scale_y = height / vb_h
        doc_transform = _multiply_matrix(_scale_matrix(scale_x, scale_y), _translate_matrix(-vb_min_x, -vb_min_y))

    paths: List[SvgPath] = []
    _walk_svg_paths(root, doc_transform, paths)
    return paths, width, height


def _fmt_float(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    if text in ("-0", ""):
        return "0"
    return text


def _format_matrix(matrix: Tuple[float, float, float, float, float, float]) -> str:
    return " ".join(_fmt_float(v) for v in matrix)


def serialize_svg_paths(paths: Iterable[SvgPath]) -> str:
    """Serialize SvgPath objects into SVG <path> strings."""
    parts = []
    for path in paths:
        attrs = [f'd="{path.d}"']
        if path.fill:
            attrs.append(f'fill="{path.fill}"')
        if path.style:
            attrs.append(f'style="{path.style}"')
        if not _matrix_is_identity(path.transform):
            attrs.append(f'transform="matrix({_format_matrix(path.transform)})"')
        parts.append(f'<path {" ".join(attrs)}/>')
    return "\n".join(parts)


def extract_svg_paths(svg_content: str) -> str:
    """Extract path elements from an SVG string, resolving viewBox/transform."""
    paths, _, _ = parse_svg_document(svg_content)
    return serialize_svg_paths(paths)


def _tokenize_svg_path(d_str: str) -> List[Tuple[str, List[float]]]:
    """
    Tokenize SVG path 'd' attribute into a list of (command, params) tuples.
    Example: "M 10 20 L 30 40" -> [('M', [10.0, 20.0]), ('L', [30.0, 40.0])]
    """
    normalized = re.sub(r'([MLCZHVSQTAmlczhvsqta])', r' \1 ', d_str)
    normalized = normalized.replace(',', ' ')
    parts = normalized.split()

    result = []
    current_cmd = None
    current_params = []

    param_counts = {
        'M': 2, 'm': 2, 'L': 2, 'l': 2,
        'C': 6, 'c': 6, 'S': 4, 's': 4,
        'Q': 4, 'q': 4, 'T': 2, 't': 2,
        'H': 1, 'h': 1, 'V': 1, 'v': 1,
        'Z': 0, 'z': 0, 'A': 7, 'a': 7
    }

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part in param_counts:
            if current_cmd is not None:
                result.append((current_cmd, current_params))
            current_cmd = part
            current_params = []
        else:
            try:
                current_params.append(float(part))
            except ValueError:
                continue

            if current_cmd and len(current_params) >= param_counts.get(current_cmd, 0):
                expected = param_counts.get(current_cmd, 0)
                if expected > 0:
                    result.append((current_cmd, current_params[:expected]))
                    current_params = current_params[expected:]
                    if current_cmd == 'M':
                        current_cmd = 'L'
                    elif current_cmd == 'm':
                        current_cmd = 'l'

    if current_cmd is not None and current_cmd.upper() == 'Z':
        result.append((current_cmd, []))
    elif current_cmd is not None and current_params:
        result.append((current_cmd, current_params))

    return result


def parse_d_to_ae_paths(d_str: str) -> List[dict]:
    """
    Parse SVG path 'd' attribute into a list of After Effects path data objects.
    Each sub-path (starting with M/m) becomes a separate path object.
    """
    tokens = _tokenize_svg_path(d_str)

    sub_paths = []
    current_path = None

    pen_x, pen_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0

    last_cmd = None
    last_cubic_cp = None
    last_quad_cp = None

    def new_subpath():
        nonlocal current_path
        if current_path and current_path["vertices"]:
            sub_paths.append(current_path)
        current_path = {
            "vertices": [],
            "inTangents": [],
            "outTangents": [],
            "closed": False
        }

    for cmd, params in tokens:
        is_rel = cmd.islower()
        cmd_type = cmd.upper()

        if cmd_type == 'M':
            if len(params) < 2:
                continue
            new_subpath()
            if is_rel:
                pen_x += params[0]
                pen_y += params[1]
            else:
                pen_x, pen_y = params[0], params[1]

            start_x, start_y = pen_x, pen_y
            current_path["vertices"].append([pen_x, pen_y])
            current_path["inTangents"].append([0, 0])
            current_path["outTangents"].append([0, 0])
            last_cubic_cp = None
            last_quad_cp = None

        elif cmd_type == 'L':
            if len(params) < 2 or current_path is None:
                continue
            if is_rel:
                pen_x += params[0]
                pen_y += params[1]
            else:
                pen_x, pen_y = params[0], params[1]

            current_path["vertices"].append([pen_x, pen_y])
            current_path["inTangents"].append([0, 0])
            current_path["outTangents"].append([0, 0])
            last_cubic_cp = None
            last_quad_cp = None

        elif cmd_type == 'H':
            if len(params) < 1 or current_path is None:
                continue
            if is_rel:
                pen_x += params[0]
            else:
                pen_x = params[0]

            current_path["vertices"].append([pen_x, pen_y])
            current_path["inTangents"].append([0, 0])
            current_path["outTangents"].append([0, 0])
            last_cubic_cp = None
            last_quad_cp = None

        elif cmd_type == 'V':
            if len(params) < 1 or current_path is None:
                continue
            if is_rel:
                pen_y += params[0]
            else:
                pen_y = params[0]

            current_path["vertices"].append([pen_x, pen_y])
            current_path["inTangents"].append([0, 0])
            current_path["outTangents"].append([0, 0])
            last_cubic_cp = None
            last_quad_cp = None

        elif cmd_type == 'C':
            if len(params) < 6 or current_path is None:
                continue
            if is_rel:
                cp1_x, cp1_y = pen_x + params[0], pen_y + params[1]
                cp2_x, cp2_y = pen_x + params[2], pen_y + params[3]
                end_x, end_y = pen_x + params[4], pen_y + params[5]
            else:
                cp1_x, cp1_y = params[0], params[1]
                cp2_x, cp2_y = params[2], params[3]
                end_x, end_y = params[4], params[5]

            if current_path["vertices"]:
                prev_x, prev_y = current_path["vertices"][-1]
                current_path["outTangents"][-1] = [cp1_x - prev_x, cp1_y - prev_y]

            current_path["vertices"].append([end_x, end_y])
            current_path["inTangents"].append([cp2_x - end_x, cp2_y - end_y])
            current_path["outTangents"].append([0, 0])

            pen_x, pen_y = end_x, end_y
            last_cubic_cp = (cp2_x, cp2_y)
            last_quad_cp = None

        elif cmd_type == 'S':
            if len(params) < 4 or current_path is None:
                continue
            if last_cmd in ('C', 'S') and last_cubic_cp:
                cp1_x = 2 * pen_x - last_cubic_cp[0]
                cp1_y = 2 * pen_y - last_cubic_cp[1]
            else:
                cp1_x, cp1_y = pen_x, pen_y

            if is_rel:
                cp2_x, cp2_y = pen_x + params[0], pen_y + params[1]
                end_x, end_y = pen_x + params[2], pen_y + params[3]
            else:
                cp2_x, cp2_y = params[0], params[1]
                end_x, end_y = params[2], params[3]

            if current_path["vertices"]:
                prev_x, prev_y = current_path["vertices"][-1]
                current_path["outTangents"][-1] = [cp1_x - prev_x, cp1_y - prev_y]

            current_path["vertices"].append([end_x, end_y])
            current_path["inTangents"].append([cp2_x - end_x, cp2_y - end_y])
            current_path["outTangents"].append([0, 0])

            pen_x, pen_y = end_x, end_y
            last_cubic_cp = (cp2_x, cp2_y)
            last_quad_cp = None

        elif cmd_type == 'Q':
            if len(params) < 4 or current_path is None:
                continue
            if is_rel:
                qcp_x, qcp_y = pen_x + params[0], pen_y + params[1]
                end_x, end_y = pen_x + params[2], pen_y + params[3]
            else:
                qcp_x, qcp_y = params[0], params[1]
                end_x, end_y = params[2], params[3]

            cp1_x = pen_x + (2.0 / 3.0) * (qcp_x - pen_x)
            cp1_y = pen_y + (2.0 / 3.0) * (qcp_y - pen_y)
            cp2_x = end_x + (2.0 / 3.0) * (qcp_x - end_x)
            cp2_y = end_y + (2.0 / 3.0) * (qcp_y - end_y)

            if current_path["vertices"]:
                prev_x, prev_y = current_path["vertices"][-1]
                current_path["outTangents"][-1] = [cp1_x - prev_x, cp1_y - prev_y]

            current_path["vertices"].append([end_x, end_y])
            current_path["inTangents"].append([cp2_x - end_x, cp2_y - end_y])
            current_path["outTangents"].append([0, 0])

            pen_x, pen_y = end_x, end_y
            last_quad_cp = (qcp_x, qcp_y)
            last_cubic_cp = (cp2_x, cp2_y)

        elif cmd_type == 'T':
            if len(params) < 2 or current_path is None:
                continue
            if last_cmd in ('Q', 'T') and last_quad_cp:
                qcp_x = 2 * pen_x - last_quad_cp[0]
                qcp_y = 2 * pen_y - last_quad_cp[1]
            else:
                qcp_x, qcp_y = pen_x, pen_y

            if is_rel:
                end_x, end_y = pen_x + params[0], pen_y + params[1]
            else:
                end_x, end_y = params[0], params[1]

            cp1_x = pen_x + (2.0 / 3.0) * (qcp_x - pen_x)
            cp1_y = pen_y + (2.0 / 3.0) * (qcp_y - pen_y)
            cp2_x = end_x + (2.0 / 3.0) * (qcp_x - end_x)
            cp2_y = end_y + (2.0 / 3.0) * (qcp_y - end_y)

            if current_path["vertices"]:
                prev_x, prev_y = current_path["vertices"][-1]
                current_path["outTangents"][-1] = [cp1_x - prev_x, cp1_y - prev_y]

            current_path["vertices"].append([end_x, end_y])
            current_path["inTangents"].append([cp2_x - end_x, cp2_y - end_y])
            current_path["outTangents"].append([0, 0])

            pen_x, pen_y = end_x, end_y
            last_quad_cp = (qcp_x, qcp_y)
            last_cubic_cp = (cp2_x, cp2_y)

        elif cmd_type == 'Z':
            if current_path:
                current_path["closed"] = True
            pen_x, pen_y = start_x, start_y
            last_cubic_cp = None
            last_quad_cp = None

        last_cmd = cmd_type

    if current_path and current_path["vertices"]:
        sub_paths.append(current_path)

    return sub_paths


def _apply_transform_to_shape(shape: dict, matrix: Tuple[float, float, float, float, float, float]) -> dict:
    if _matrix_is_identity(matrix):
        return shape

    new_vertices = []
    for vx, vy in shape["vertices"]:
        new_vertices.append(list(_apply_matrix(matrix, vx, vy)))

    new_in = []
    for tx, ty in shape["inTangents"]:
        new_in.append(list(_apply_linear(matrix, tx, ty)))

    new_out = []
    for tx, ty in shape["outTangents"]:
        new_out.append(list(_apply_linear(matrix, tx, ty)))

    shape["vertices"] = new_vertices
    shape["inTangents"] = new_in
    shape["outTangents"] = new_out
    return shape


def svg_paths_to_ae_shapes(paths: List[SvgPath]) -> list:
    """
    Convert SvgPath objects into After Effects shape groups.
    Each SvgPath becomes a group containing all its sub-paths and a SINGLE fill.
    """
    shapes = []
    for path in paths:
        sub_paths = parse_d_to_ae_paths(path.d)
        group_paths = []
        for sp in sub_paths:
            if not sp["vertices"]:
                continue
            shape = {
                "vertices": sp["vertices"],
                "inTangents": sp["inTangents"],
                "outTangents": sp["outTangents"],
                "closed": sp["closed"]
            }
            # Transform individual sub-paths
            group_paths.append(_apply_transform_to_shape(shape, path.transform))
        
        if group_paths:
            shapes.append({
                "type": "group",
                "fill": path.fill,
                "opacity": path.opacity,
                "paths": group_paths
            })
    return shapes


def parse_svg_to_ae_shapes(svg_content: str) -> list:
    """Parse SVG content into After Effects shape data (no normalization)."""
    paths, _, _ = parse_svg_document(svg_content)
    return svg_paths_to_ae_shapes(paths)


def _iter_leaf_layers(layers: List[LayerSVG]) -> Iterable[LayerSVG]:
    for layer in layers:
        if layer.is_group:
            yield from _iter_leaf_layers(layer.children)
        else:
            yield layer


def save_individual_svgs(layers: List[LayerSVG], output_dir: Path) -> list:
    """Save each leaf layer as an individual SVG file."""
    output_dir = Path(output_dir)
    svg_subdir = output_dir / "layers"
    svg_subdir.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for i, layer in enumerate(_iter_leaf_layers(layers)):
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', layer.path)
        safe_name = f"{i:03d}_{safe_name}"

        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{int(layer.width)}" height="{int(layer.height)}"
     viewBox="0 0 {int(layer.width)} {int(layer.height)}">
  <!-- Layer: {layer.path} -->
  {serialize_svg_paths(layer.svg_paths)}
</svg>'''

        svg_path = svg_subdir / f"{safe_name}.svg"
        svg_path.write_text(svg_content, encoding='utf-8')

        saved_files.append({
            'name': layer.name,
            'uid': layer.uid,
            'path': layer.path,
            'path_file': str(svg_path),
            'width': layer.width,
            'height': layer.height,
            'offset_x': layer.offset_x,
            'offset_y': layer.offset_y,
            'anchor_x': layer.anchor_x,
            'anchor_y': layer.anchor_y,
            'duik_name': layer.duik_name
        })

    return saved_files


def build_structured_svg(layers: List[LayerSVG], canvas_width: int, canvas_height: int, output_path: Path) -> str:
    """Build a single SVG file containing all layers with group hierarchy."""
    svg_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" ',
        f'     width="{canvas_width}" height="{canvas_height}" ',
        f'     viewBox="0 0 {canvas_width} {canvas_height}">',
        f'  <!-- Generated by RigReady Vectorizer -->',
        f'  <!-- Layer count: {len(list(_iter_leaf_layers(layers)))} -->',
        f''
    ]

    def render_node(node: LayerSVG, parent_x: float, parent_y: float, depth: int) -> None:
        indent = "  " * depth
        rel_x = node.offset_x - parent_x
        rel_y = node.offset_y - parent_y
        transform = ""
        if rel_x != 0 or rel_y != 0:
            transform = f' transform="translate({_fmt_float(rel_x)}, {_fmt_float(rel_y)})"'

        node_id = _safe_id(node.uid or node.path or node.name)
        data_name = f' data-name="{node.name}"'
        data_path = f' data-path="{node.path}"'
        duik_attr = f' data-duik="{node.duik_name}"' if node.duik_name else ''

        if node.is_group:
            svg_parts.append(f'{indent}<g id="{node_id}"{transform}{data_name}{data_path}>')
            for child in node.children:
                render_node(child, node.offset_x, node.offset_y, depth + 1)
            svg_parts.append(f'{indent}</g>')
        else:
            anchor_attrs = ""
            if node.anchor_x is not None and node.anchor_y is not None:
                anchor_attrs = f' data-anchor-x="{_fmt_float(node.anchor_x)}" data-anchor-y="{_fmt_float(node.anchor_y)}"'
            svg_parts.append(f'{indent}<g id="{node_id}"{transform}{duik_attr}{data_name}{data_path}{anchor_attrs}>')
            svg_parts.append(f'{indent}  {serialize_svg_paths(node.svg_paths)}')
            svg_parts.append(f'{indent}</g>')

    for layer in layers:
        render_node(layer, 0.0, 0.0, 1)

    svg_parts.append('</svg>')

    svg_content = '\n'.join(svg_parts)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding='utf-8')

    return svg_content


def build_metadata_json(layers: List[LayerSVG], canvas_width: int, canvas_height: int, output_path: Path) -> dict:
    """Generate JSON metadata for After Effects scripting."""
    def serialize(node: LayerSVG) -> dict:
        data = {
            "name": node.name,
            "uid": node.uid,
            "path": node.path,
            "position": {"x": node.offset_x, "y": node.offset_y},
            "size": {"width": node.width, "height": node.height},
            "is_group": node.is_group
        }
        if node.parent_uid:
            data["parent_uid"] = node.parent_uid
        if node.anchor_x is not None and node.anchor_y is not None:
            data["anchor"] = {"x": node.anchor_x, "y": node.anchor_y}
        if node.duik_name:
            data["duik_name"] = node.duik_name
        if node.children:
            data["children"] = [serialize(child) for child in node.children]
        return data

    metadata = {
        "version": "1.1",
        "generator": "RigReady Vectorizer",
        "canvas": {"width": canvas_width, "height": canvas_height},
        "layers": [serialize(layer) for layer in layers]
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata


def build_ae_jsx_script(
    layer_data: list, 
    canvas_width: int, 
    canvas_height: int, 
    output_path: Path,
    msg_complete: str = "Native Import Complete!",
    msg_error: str = "Error during native import"
) -> str:
    """
    Generate After Effects ExtendScript for creating native Shape Layers.
    Each shape becomes its own group with its own path and fill.
    """
    processed_layers = []
    for layer in layer_data:
        local_ax = layer["anchor_x"] - layer["offset_x"] if layer.get("anchor_x") is not None else 0
        local_ay = layer["anchor_y"] - layer["offset_y"] if layer.get("anchor_y") is not None else 0

        processed_layers.append({
            "name": layer["name"],
            "x": layer["offset_x"],
            "y": layer["offset_y"],
            "w": layer["width"],
            "h": layer["height"],
            "anchor_x": layer.get("anchor_x", layer["offset_x"]),
            "anchor_y": layer.get("anchor_y", layer["offset_y"]),
            "local_ax": local_ax,
            "local_ay": local_ay,
            "shapes": layer.get("shapes", [])
        })

    layers_json = json.dumps(processed_layers, indent=2)

    jsx_content = f'''// RigReady Vectorizer - After Effects Native Shape Import Script
// Auto-generated - creates native Shape Layers with proper position and anchor points

(function() {{
    app.beginUndoGroup("RigReady Native Import");

    try {{
        var compWidth = {canvas_width};
        var compHeight = {canvas_height};
        var fps = 24;
        var duration = 10;

        var layers = {layers_json};

        var comp = app.project.items.addComp(
            "RigReady_Native_Vectors",
            compWidth,
            compHeight,
            1,
            duration,
            fps
        );

        function hexToAeColor(hex) {{
            hex = hex.replace('#', '');
            if (hex.length === 3) {{
                hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
            }}
            var r = parseInt(hex.substring(0, 2), 16) / 255;
            var g = parseInt(hex.substring(2, 4), 16) / 255;
            var b = parseInt(hex.substring(4, 6), 16) / 255;
            return [r, g, b];
        }}

        // Create each layer (index 0 = bottom, last = top)
        for (var i = 0; i < layers.length; i++) {{
            var lData = layers[i];

            var shapeLayer = comp.layers.addShape();
            shapeLayer.name = lData.name;

            // Set anchor/position in comp space
            shapeLayer.property("ADBE Transform Group")
                .property("ADBE Anchor Point")
                .setValue([lData.local_ax, lData.local_ay]);
            shapeLayer.property("ADBE Transform Group")
                .property("ADBE Position")
                .setValue([lData.anchor_x, lData.anchor_y]);

            var contents = shapeLayer.property("ADBE Root Vectors Group");

            for (var j = lData.shapes.length - 1; j >= 0; j--) {{
                var sGroup = lData.shapes[j];

                // Create a container group for the compound path
                var group = contents.addProperty("ADBE Vector Group");
                group.name = "Path Group " + (j + 1);
                var groupContents = group.property("ADBE Vectors Group");

                // Add all sub-paths first
                for (var k = 0; k < sGroup.paths.length; k++) {{
                    var sData = sGroup.paths[k];
                    var pathProp = groupContents.addProperty("ADBE Vector Shape - Group");
                    var myShape = new Shape();
                    myShape.vertices = sData.vertices;
                    myShape.inTangents = sData.inTangents;
                    myShape.outTangents = sData.outTangents;
                    myShape.closed = sData.closed;
                    pathProp.property("ADBE Vector Shape").setValue(myShape);
                }}

                // Add single fill for the entire group (handles holes)
                var fillProp = groupContents.addProperty("ADBE Vector Graphic - Fill");
                fillProp.property("ADBE Vector Fill Color").setValue(hexToAeColor(sGroup.fill));
                if (sGroup.opacity !== undefined) {{
                    fillProp.property("ADBE Vector Fill Opacity").setValue(sGroup.opacity * 100);
                }}
            }}
        }}

        comp.openInViewer();
        alert("{msg_complete}\\n\\n" +
              "Layers created: " + layers.length + "\\n" +
              "Each layer is a native After Effects Shape Layer.");

    }} catch (e) {{
        alert("{msg_error}:\\n" + e.toString() + "\\nLine: " + e.line);
    }}

    app.endUndoGroup();
}})();
'''

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(jsx_content, encoding='utf-8')

    return jsx_content


if __name__ == "__main__":
    # Simple parser sanity check
    test_d = "M 10 10 L 100 10 L 100 100 Z M 50 50 Q 60 50 70 70 Z"
    paths = parse_d_to_ae_paths(test_d)
    print(f"Parsed {len(paths)} sub-paths")
