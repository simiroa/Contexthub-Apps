#!/usr/bin/env python
"""
Gemini Image Tools - Legacy Entry Point

This file provides backward compatibility for the old import style.
The actual implementation has been refactored into a package.

Usage:
    # Direct execution (from context menu)
    python gemini_img_tools.py "path/to/image.png"
    
    # As module import
    from gemini_img_tools import GeminiImageToolsGUI
"""
import sys
import os
from pathlib import Path

# Setup paths for proper imports when run directly
current_dir = Path(__file__).parent.resolve()
src_dir = current_dir.parent.parent.parent

# Add paths in correct order
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import from the package using relative path (same directory)
try:
    from gemini_img_tools.gui import GeminiImageToolsGUI
    from gemini_img_tools.core import get_gemini_client, imread_unicode, get_unique_path
    from gemini_img_tools.pbr import (
        generate_normal_map,
        generate_roughness_map,
        generate_displacement_map,
        generate_occlusion_map,
        generate_metallic_map,
        make_tileable_synthesis
    )
    from gemini_img_tools.history import HistoryManager
    from gemini_img_tools.viewer import ImageViewer
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current dir: {current_dir}")
    print(f"Src dir: {src_dir}")
    print(f"sys.path: {sys.path[:5]}")
    raise

__all__ = [
    'GeminiImageToolsGUI',
    'get_gemini_client',
    'imread_unicode',
    'get_unique_path',
    'generate_normal_map',
    'generate_roughness_map',
    'generate_displacement_map',
    'generate_occlusion_map',
    'generate_metallic_map',
    'make_tileable_synthesis',
    'HistoryManager',
    'ImageViewer',
]

def main():
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
        print(f"Starting Gemini Image Tools with: {target_path}")
        try:
            app = GeminiImageToolsGUI(target_path)
            app.mainloop()
        except Exception as e:
            print(f"Error launching GUI: {e}")
            import traceback
            traceback.print_exc()
            # Keep window open for debugging
            input("Press Enter to close...")
    else:
        print("Usage: python gemini_img_tools.py <image_path>")

if __name__ == "__main__":
    main()
