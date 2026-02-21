"""
Anchor Point Estimator - Automatic rigging anchor point detection.
Uses layer naming conventions and bounding box analysis.
"""
from dataclasses import dataclass
from typing import Optional
import re


# Keyword mappings for body part detection (case-insensitive)
# Format: keyword -> (anchor_x_ratio, anchor_y_ratio) relative to bounding box
BODY_PART_KEYWORDS = {
    # Head/Face
    "head": (0.5, 0.8),      # Anchor at neck area
    "face": (0.5, 0.8),
    "hair": (0.5, 0.9),
    "eye": (0.5, 0.5),
    "ear": (0.5, 0.5),
    "nose": (0.5, 0.5),
    "mouth": (0.5, 0.5),
    
    # Upper body
    "neck": (0.5, 0.5),
    "body": (0.5, 0.3),
    "torso": (0.5, 0.3),
    "chest": (0.5, 0.5),
    "shoulder": (0.5, 0.5),
    
    # Arms
    "arm": (0.5, 0.1),       # Anchor at shoulder joint
    "upper_arm": (0.5, 0.1),
    "upperarm": (0.5, 0.1),
    "forearm": (0.5, 0.1),
    "lower_arm": (0.5, 0.1),
    "lowerarm": (0.5, 0.1),
    "elbow": (0.5, 0.5),
    
    # Hands
    "hand": (0.5, 0.1),      # Anchor at wrist
    "wrist": (0.5, 0.5),
    "finger": (0.5, 0.1),
    "thumb": (0.5, 0.1),
    
    # Legs
    "leg": (0.5, 0.1),       # Anchor at hip joint
    "upper_leg": (0.5, 0.1),
    "upperleg": (0.5, 0.1),
    "thigh": (0.5, 0.1),
    "lower_leg": (0.5, 0.1),
    "lowerleg": (0.5, 0.1),
    "calf": (0.5, 0.1),
    "shin": (0.5, 0.1),
    "knee": (0.5, 0.5),
    
    # Feet
    "foot": (0.5, 0.1),      # Anchor at ankle
    "ankle": (0.5, 0.5),
    "toe": (0.5, 0.1),
    
    # Other
    "tail": (0.5, 0.1),
    "wing": (0.2, 0.2),
    "accessory": (0.5, 0.5),
    "prop": (0.5, 0.5),
}

# Duik Angela naming convention mappings
DUIK_NAME_MAP = {
    "head": "Head",
    "neck": "Neck",
    "body": "Body",
    "torso": "Spine",
    "shoulder": "Shoulder",
    "upper_arm": "Arm",
    "forearm": "Forearm",
    "hand": "Hand",
    "upper_leg": "Thigh",
    "lower_leg": "Calf",
    "foot": "Foot",
    "toe": "Toes",
}

# Side detection patterns
SIDE_PATTERNS = {
    "left": [r"[_\-\s]?l[_\-\s]?$", r"^l[_\-\s]", r"left", r"_l_"],
    "right": [r"[_\-\s]?r[_\-\s]?$", r"^r[_\-\s]", r"right", r"_r_"],
}


@dataclass
class AnchorPoint:
    """Represents an anchor point for rigging."""
    layer_name: str
    x: float
    y: float
    body_part: Optional[str]
    side: Optional[str]  # "left", "right", or None
    duik_name: Optional[str]
    confidence: float  # 0.0 to 1.0
    
    def to_dict(self) -> dict:
        return {
            "layer": self.layer_name,
            "anchor": {"x": self.x, "y": self.y},
            "body_part": self.body_part,
            "side": self.side,
            "duik_name": self.duik_name,
            "confidence": self.confidence
        }


def detect_body_part(layer_name: str) -> tuple:
    """
    Detect body part from layer name.
    
    Returns:
        (body_part, anchor_ratio, confidence)
    """
    name_lower = layer_name.lower()
    
    # Check against keywords
    for keyword, ratio in BODY_PART_KEYWORDS.items():
        if keyword in name_lower:
            # Higher confidence for exact word match
            if re.search(rf'\b{keyword}\b', name_lower):
                return (keyword, ratio, 0.9)
            return (keyword, ratio, 0.6)
    
    return (None, (0.5, 0.5), 0.3)


def detect_side(layer_name: str) -> Optional[str]:
    """Detect left/right side from layer name."""
    name_lower = layer_name.lower()
    
    for side, patterns in SIDE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, name_lower, re.IGNORECASE):
                return side
    
    return None


def get_duik_name(body_part: str, side: Optional[str]) -> Optional[str]:
    """Get Duik Angela compatible name."""
    base_name = DUIK_NAME_MAP.get(body_part)
    if not base_name:
        return None
    
    if side:
        prefix = "L " if side == "left" else "R "
        return prefix + base_name
    
    return base_name


def estimate_anchor_point(
    layer_name: str,
    offset_x: int,
    offset_y: int,
    width: int,
    height: int
) -> AnchorPoint:
    """
    Estimate anchor point for a layer based on name and bounds.
    
    Args:
        layer_name: Name of the layer
        offset_x: Layer X offset from canvas origin
        offset_y: Layer Y offset from canvas origin
        width: Layer width
        height: Layer height
    
    Returns:
        AnchorPoint with estimated position and metadata
    """
    body_part, (ratio_x, ratio_y), confidence = detect_body_part(layer_name)
    side = detect_side(layer_name)
    duik_name = get_duik_name(body_part, side) if body_part else None
    
    # Calculate absolute anchor position
    anchor_x = offset_x + (width * ratio_x)
    anchor_y = offset_y + (height * ratio_y)
    
    return AnchorPoint(
        layer_name=layer_name,
        x=anchor_x,
        y=anchor_y,
        body_part=body_part,
        side=side,
        duik_name=duik_name,
        confidence=confidence
    )


def estimate_anchors_for_layers(layers: list) -> list:
    """
    Estimate anchor points for multiple layers.
    
    Args:
        layers: List of LayerInfo objects (from psd_parser)
    
    Returns:
        List of AnchorPoint objects
    """
    anchors = []
    
    for layer in layers:
        if layer.width > 0 and layer.height > 0:
            anchor = estimate_anchor_point(
                layer.name,
                layer.offset_x,
                layer.offset_y,
                layer.width,
                layer.height
            )
            anchors.append(anchor)
    
    return anchors


if __name__ == "__main__":
    # Test examples
    test_names = [
        "Head",
        "L_Arm",
        "right_hand",
        "Upper_Leg_R",
        "body",
        "tail",
        "random_layer"
    ]
    
    for name in test_names:
        anchor = estimate_anchor_point(name, 0, 0, 100, 100)
        print(f"{name}: body_part={anchor.body_part}, side={anchor.side}, "
              f"duik={anchor.duik_name}, confidence={anchor.confidence:.1f}")
