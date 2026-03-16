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
class OutputOptions:
    output_dir: str = ""
    file_prefix: str = "vect_"
    open_folder_after_run: bool = True
    export_session_json: bool = True

@dataclass
class VectorizerState:
    # Assets (Matches Qt template pattern)
    source_path: Optional[Path] = None
    input_assets: List[LayerStateEntry] = field(default_factory=list)
    output_assets: List[LayerStateEntry] = field(default_factory=list)
    preview_uid: Optional[str] = None
    current_mode: str = "input" # "input" or "output"
    
    # Options
    show_comparison: bool = False
    remove_bg: bool = True
    gen_jsx: bool = True
    split_paths: bool = False
    use_anchor: bool = True
    skip_text: bool = False
    skip_smart: bool = False
    
    # VTracer Settings
    speckle: int = 4
    color_precision: int = 6
    corner_threshold: int = 60
    
    # Output (Matches Qt template pattern)
    output_options: OutputOptions = field(default_factory=OutputOptions)
    
    # UI status
    is_processing: bool = False
    progress: float = 0.0
    status_text: str = "Ready"
    workflow_name: str = "Default"
    workflow_description: str = "Convert raster layers to rigged SVG paths."
    
    @property
    def preview_path(self) -> Optional[Path]:
        return self.source_path

    def update_layer_visibility(self):
        for layer in self.layers:
            if self.skip_text and layer.is_text:
                layer.visible = False
            elif self.skip_smart and layer.is_smart_object:
                layer.visible = False
            else:
                layer.visible = True
