
from abc import ABC, abstractmethod
import json

class WorkflowWidgetDef:
    """Metadata for a UI widget required by a workflow."""
    def __init__(self, key, type, label, default=None, options=None):
        self.key = key
        self.type = type # 'slider', 'image', 'text', 'lora', 'ckpt'
        self.label = label
        self.default = default
        self.options = options

class BaseWorkflowWrapper(ABC):
    def __init__(self, name, description, workflow_path):
        self.name = name
        self.description = description
        self.workflow_path = workflow_path

    @abstractmethod
    def get_ui_definition(self):
        """Returns a list of WorkflowWidgetDef."""
        pass

    @abstractmethod
    def apply_values(self, workflow_json, values):
        """Injects values into the workflow JSON and returns it."""
        pass

# --- IMPLEMENTATIONS ---

class ZImageTurboWrapper(BaseWorkflowWrapper):
    def __init__(self):
        super().__init__(
            "Z-Image Turbo (Fast)", 
            "Optimized for speed using Z-Image discrete nodes.",
            "assets/workflows/z_image/turbo.json"
        )

    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("prompt", "text", "Positive Prompt", ""),
            WorkflowWidgetDef("loras", "lora", "LoRA Stack"),
            WorkflowWidgetDef("steps", "slider", "Steps", 4, {"from": 1, "to": 12, "res": 1}),
            WorkflowWidgetDef("resolution", "combo", "Output Size", "1024x1024", ["1024x1024", "896x1152"])
        ]

    def apply_values(self, wf, val):
        # Specific injection logic for Z-Turbo (Hardcoded IDs for reliability)
        if "45" in wf: wf["45"]["inputs"]["text"] = val.get("prompt", "")
        if "44" in wf: wf["44"]["inputs"]["seed"] = val.get("seed", 0)
        return wf

class SDXLAdvancedWrapper(BaseWorkflowWrapper):
    def __init__(self):
        super().__init__(
            "SDXL Professional (Efficiency)",
            "Advanced SDXL with FaceDetailer and high-quality samplers.",
            "assets/workflows/sdxl_advanced.json"
        )

    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("ckpt", "ckpt", "Base Model"),
            WorkflowWidgetDef("prompt", "text", "Positive Prompt"),
            WorkflowWidgetDef("negative", "text", "Negative Prompt"),
            WorkflowWidgetDef("loras", "lora", "LoRA Stack"),
            WorkflowWidgetDef("steps", "slider", "Sampling Steps", 25, {"from": 1, "to": 50}),
            WorkflowWidgetDef("cfg", "slider", "CFG Scale", 7.0, {"from": 1, "to": 20, "res": 0.5}),
            WorkflowWidgetDef("detailer", "checkbox", "Face Detailer", True)
        ]

    def apply_values(self, wf, val):
        # Injection logic for Efficiency Nodes / Impact Pack
        # ... logic to find 'Efficient Loader' and 'KSampler' ...
        return wf

class DummyAllWidgetsWrapper(BaseWorkflowWrapper):
    def __init__(self):
        super().__init__(
            "DEBUG: All Widgets (Dummy)",
            "A test wrapper displaying all available widget types.",
            "assets/workflows/z_image/turbo.json" # Re-use valid path to avoid file error
        )

    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("model", "ckpt", "Checkpoint", "sd_xl.safetensors", ["sd_xl.safetensors", "dreamshaper.ckpt"]),
            WorkflowWidgetDef("prompt", "text", "Prompt Stack"),
            WorkflowWidgetDef("loras", "lora", "LoRA Stack"),
            WorkflowWidgetDef("sampler", "combo", "Sampler", "euler", ["euler", "dpmpp_2m", "ddim"]),
            WorkflowWidgetDef("cfg", "slider", "CFG Scale", 7.0, {"from": 1, "to": 20, "res": 0.5}),
            WorkflowWidgetDef("input_img", "image", "Input Image"),
            WorkflowWidgetDef("input_vid", "video", "Input Video"),
            WorkflowWidgetDef("mask_txt", "string", "Mask Target (Text)", "person"),
            WorkflowWidgetDef("seed", "seed", "Random Seed", -1),
            WorkflowWidgetDef("aspect", "aspect", "Aspect Ratio", "1:1"),
            WorkflowWidgetDef("mask_sketch", "sketch", "Inpaint Mask / Sketch"),
            WorkflowWidgetDef("toggle", "checkbox", "Enable Magic", True)
        ]

    def apply_values(self, wf, val):
        return wf

# --- MANAGER ---

class WorkflowRegistry:
    def __init__(self):
        self.wrappers = {
            "z_turbo": ZImageTurboWrapper(),
            "sdxl_adv": SDXLAdvancedWrapper(),
            "debug": DummyAllWidgetsWrapper()
        }

    def get_all_names(self):
        return [w.name for w in self.wrappers.values()]

    def get_by_name(self, name):
        for w in self.wrappers.values():
            if w.name == name: return w
        return None
