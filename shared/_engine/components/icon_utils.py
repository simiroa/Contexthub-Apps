import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray, Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

_ICON_DIR = Path(__file__).parent.parent / "assets" / "icons"


def get_icon(icon_name: str, color: Optional[str] = None, size: int = 16) -> QIcon:
    """
    Load a Lucide SVG icon and optionally tint it to a specific hex color or named color.
    
    Args:
        icon_name: Name of the icon file (without .svg extension)
        color: Optional hex string (e.g., "#ffffff" or "#94a3b8"). If None, uses original SVG color.
        size: Size of the rendered icon in pixels (default: 16)
        
    Returns:
        QIcon containing the rendered SVG.
    """
    icon_path = _ICON_DIR / f"{icon_name}.svg"
    if not icon_path.exists():
        # Fallback to empty icon if not found
        return QIcon()
        
    svg_data = icon_path.read_text(encoding="utf-8")
    
    # Replace default stroke color if a custom color is requested
    if color:
        # standard Lucide icons use `stroke="currentColor"`
        svg_data = svg_data.replace('stroke="currentColor"', f'stroke="{color}"')
        
    byte_array = QByteArray(svg_data.encode("utf-8"))
    renderer = QSvgRenderer(byte_array)
    
    # Render with high-DPI awareness support by using scalable pixmap
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)
