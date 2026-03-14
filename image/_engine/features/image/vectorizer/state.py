from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass, field

@dataclass
class LayerStateEntry:
    uid: str
    name: str
    display_name: str
    width: int
    height: int
    data: any  # LayerInfo or Path
    is_text: bool = False
    is_smart_object: bool = False
    selected: bool = True
    visible: bool = True

@dataclass
class VectorizerState:
    # Files and Layers
    source_files: List[Path] = field(default_factory=list)
    layers: List[LayerStateEntry] = field(default_factory=list)
    
    # VTracer Settings
    speckle: int = 4
    color_precision: int = 6
    corner_threshold: int = 60
    
    # Options
    remove_bg: bool = True
    gen_jsx: bool = True
    split_paths: bool = False
    use_anchor: bool = True
    skip_text: bool = False
    skip_smart: bool = False
    
    # Path
    output_dir: str = ""
    
    # UI status
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    
    def update_layer_visibility(self):
        for layer in self.layers:
            if self.skip_text and layer.is_text:
                layer.visible = False
            elif self.skip_smart and layer.is_smart_object:
                layer.visible = False
            else:
                layer.visible = True
