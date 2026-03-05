"""
Gemini Image Tools Package
Modular texture generation and PBR tools using Gemini AI.

Usage:
    from ai_standalone.gemini_img_tools import GeminiImageToolsGUI
    
    app = GeminiImageToolsGUI(target_path)
    app.mainloop()
"""

from .gui import GeminiImageToolsGUI
from .core import get_gemini_client, imread_unicode, get_unique_path
from .pbr import (
    generate_normal_map,
    generate_roughness_map,
    generate_displacement_map,
    generate_occlusion_map,
    generate_metallic_map,
    make_tileable_synthesis
)
from .history import HistoryManager
from .viewer import ImageViewer
from .prompts import (
    generate_style_prompt,
    generate_pbr_prompt,
    generate_tile_prompt,
    generate_weather_prompt,
    generate_analyze_prompt,
    generate_outpaint_prompt,
    generate_inpaint_prompt
)

__all__ = [
    # Main GUI
    'GeminiImageToolsGUI',
    
    # Core utilities
    'get_gemini_client',
    'imread_unicode',
    'get_unique_path',
    
    # PBR functions
    'generate_normal_map',
    'generate_roughness_map',
    'generate_displacement_map',
    'generate_occlusion_map',
    'generate_metallic_map',
    'make_tileable_synthesis',
    
    # Components
    'HistoryManager',
    'ImageViewer',
    
    # Prompt generators
    'generate_style_prompt',
    'generate_pbr_prompt',
    'generate_tile_prompt',
    'generate_weather_prompt',
    'generate_analyze_prompt',
    'generate_outpaint_prompt',
    'generate_inpaint_prompt',
]

__version__ = '2.0.0'
