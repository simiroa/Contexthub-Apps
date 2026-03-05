
from abc import ABC, abstractmethod
import os
import time
import random
from pathlib import Path
from PIL import Image

# Try import rembg for post-processing
try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

class WorkflowWidgetDef:
    def __init__(self, key, type, label, default=None, options=None):
        self.key = key
        self.type = type # 'slider', 'image', 'text', 'lora', 'ckpt', 'checkbox', 'combo'
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
        """Injects UI values into the ComfyUI JSON."""
        pass

    def post_process(self, images, values):
        """Optional post-processing stage. Returns list of processed PIL Images."""
        return images

class ZImageTurboWrapper(BaseWorkflowWrapper):
    def __init__(self):
        super().__init__(
            "Z-Image Turbo (Fast)", 
            "Optimized for speed using Z-Image discrete nodes.",
            "assets/workflows/z_image/turbo.json"
        )

    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("prompt", "text", "Prompt"),
            WorkflowWidgetDef("seed", "slider", "Seed", 0, {"from": 0, "to": 2147483647, "res": 1}),
            WorkflowWidgetDef("steps", "slider", "Steps", 4, {"from": 1, "to": 12, "res": 1}),
            WorkflowWidgetDef("cfg", "slider", "CFG", 2.0, {"from": 1, "to": 10, "res": 0.1}),
            WorkflowWidgetDef("width", "item", "Width", 1024),
            WorkflowWidgetDef("height", "item", "Height", 1024),
            WorkflowWidgetDef("batch_size", "item", "Batch Size", 1),
            # Post-processing toggles
            WorkflowWidgetDef("upscale", "checkbox", "Upscale (2x)", False),
            WorkflowWidgetDef("rembg", "checkbox", "Remove Background", False),
            WorkflowWidgetDef("save_ico", "checkbox", "Save as .ico", False)
        ]

    def apply_values(self, wf, val):
        # Specific injection logic for z_image/turbo.json
        if "45" in wf: wf["45"]["inputs"]["text"] = val.get("prompt", "")
        if "44" in wf:
            wf["44"]["inputs"]["seed"] = int(val.get("seed", 0))
            wf["44"]["inputs"]["steps"] = int(val.get("steps", 4))
            wf["44"]["inputs"]["cfg"] = float(val.get("cfg", 2.0))
        if "41" in wf:
            wf["41"]["inputs"]["width"] = int(val.get("width", 1024))
            wf["41"]["inputs"]["height"] = int(val.get("height", 1024))
            wf["41"]["inputs"]["batch_size"] = int(val.get("batch_size", 1))
        return wf

    def post_process(self, images, val):
        processed = []
        for img in images:
            final = img
            if val.get("upscale"):
                w, h = final.size
                final = final.resize((w*2, h*2), Image.Resampling.LANCZOS)
            
            if val.get("rembg") and REMBG_AVAILABLE:
                try:
                    final = remove(final)
                except Exception as e:
                    print(f"Rembg error: {e}")
            
            if val.get("save_ico"):
                try:
                    export_dir = Path.home() / "Pictures" / "ContextUp_Exports"
                    export_dir.mkdir(parents=True, exist_ok=True)
                    fn = export_dir / f"icon_{int(time.time())}_{random.randint(0,99)}.ico"
                    final.save(fn, format='ICO')
                except Exception as e:
                    print(f"ICO save error: {e}")
            
            processed.append(final)
        return processed

class ACEStepBaseWrapper(BaseWorkflowWrapper):
    """Base for ACE-Step audio workflows."""
    def apply_values(self, wf, val):
        # 1. Convert Saved -> API format (Rough heuristic)
        api = self._dynamic_convert(wf)
        
        # 2. Inject Common Params
        # Node 14 (TextEncodeAceStepAudio) - Common for all 3
        if "14" in api:
            api["14"]["inputs"]["style"] = val.get("style", "")
            api["14"]["inputs"]["text"] = val.get("lyrics", "")
            # vocal_weight/dropout (widget 2)
            api["14"]["inputs"]["dropout"] = val.get("vocal_weight", 0.99)

        # Node 52 (KSampler) - Common for all 3
        if "52" in api:
            api["52"]["inputs"]["seed"] = int(val.get("seed", 0))
            api["52"]["inputs"]["steps"] = int(val.get("steps", 50))
            api["52"]["inputs"]["cfg"] = float(val.get("cfg", 5.0))
            if "denoise" in val:
                api["52"]["inputs"]["denoise"] = float(val.get("denoise", 1.0))

        # Node 17 (EmptyAceStepLatentAudio) - For Generative tasks
        if "17" in api:
            api["17"]["inputs"]["seconds"] = int(val.get("seconds", 30))

        # Node 59 (SaveAudioMP3)
        if "59" in api:
            api["59"]["inputs"]["filename_prefix"] = f"ace_{int(time.time())}"

        return api

    def _dynamic_convert(self, data):
        """Standard Saved -> API format mapper for ACE nodes."""
        api = {}; links = {}
        for l in data.get("links", []): links[l[0]] = (str(l[1]), l[2])
        for node in data.get("nodes", []):
            nid = str(node["id"])
            inputs = {}
            if "inputs" in node:
                for inp in node["inputs"]:
                    if inp.get("link") and inp["link"] in links:
                        inputs[inp["name"]] = list(links[inp["link"]])
            
            vals = node.get("widgets_values", [])
            ct = node["type"]
            # Map widgets to API names
            if ct == "LoadAudio": inputs["audio"] = vals[0] if vals else ""
            elif ct == "CheckpointLoaderSimple": inputs["ckpt_name"] = vals[0] if vals else "ace_step_v1_3.5b.safetensors"
            elif ct == "ModelSamplingSD3": inputs["shift"] = vals[0] if vals else 5.0
            elif ct == "LatentOperationTonemapReinhard": inputs["multiplier"] = vals[0] if vals else 1.0
            elif ct == "EmptyAceStepLatentAudio":
                if len(vals) >= 1: inputs["seconds"] = vals[0]
                if len(vals) >= 2: inputs["batch_size"] = vals[1]
            elif ct == "TextEncodeAceStepAudio":
                if len(vals) >= 1: inputs["style"] = vals[0]
                if len(vals) >= 2: inputs["text"] = vals[1]
                if len(vals) >= 3: inputs["dropout"] = vals[2]
            elif ct == "KSampler":
                if len(vals) >= 7:
                    inputs["seed"] = vals[0]
                    inputs["steps"] = vals[2]
                    inputs["cfg"] = vals[3]
                    inputs["sampler_name"] = vals[4]
                    inputs["scheduler"] = vals[5]
                    inputs["denoise"] = vals[6]
            elif ct == "SaveAudioMP3": inputs["filename_prefix"] = vals[0] if vals else "ace_out"
            
            api[nid] = {"class_type": ct, "inputs": inputs}
        return api

class ACEStepInstrumentalWrapper(ACEStepBaseWrapper):
    def __init__(self):
        super().__init__(
            "ACE Instrumental (Gen)",
            "Generate musical instrumentals from text description.",
            "assets/workflows/audio/ace_step_1_t2a_instrumentals.json"
        )
    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("style", "text", "Musical Style", "piano, upbeat, pop"),
            WorkflowWidgetDef("lyrics", "text", "Instrumental Tags", "[instrumental]\n[drum fill]"),
            WorkflowWidgetDef("seconds", "slider", "Duration (s)", 30, {"from": 5, "to": 120, "res": 5}),
            WorkflowWidgetDef("seed", "slider", "Seed", 0, {"from": 0, "to": 2147483647, "res": 1}),
            WorkflowWidgetDef("steps", "slider", "Steps", 50, {"from": 10, "to": 50, "res": 1}),
            WorkflowWidgetDef("cfg", "slider", "CFG", 5.0, {"from": 1.0, "to": 10.0, "res": 0.1})
        ]

class ACEStepSongWrapper(ACEStepBaseWrapper):
    def __init__(self):
        super().__init__(
            "ACE Vocal Song (Gen)",
            "Generate full songs with vocals from lyrics and style.",
            "assets/workflows/audio/ace_step_1_t2a_song.json"
        )
    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("style", "text", "Style Prompt", "female vocals, kawaii pop, cheerful"),
            WorkflowWidgetDef("lyrics", "text", "Lyrics", "[ko]\n반가워요 ACE Step 입니다."),
            WorkflowWidgetDef("vocal_weight", "slider", "Vocal Weight", 0.99, {"from": 0.5, "to": 1.0, "res": 0.01}),
            WorkflowWidgetDef("seconds", "slider", "Duration (s)", 120, {"from": 5, "to": 300, "res": 5}),
            WorkflowWidgetDef("seed", "slider", "Seed", 0, {"from": 0, "to": 2147483647, "res": 1}),
            WorkflowWidgetDef("steps", "slider", "Steps", 50, {"from": 10, "to": 50, "res": 1}),
            WorkflowWidgetDef("cfg", "slider", "CFG", 5.0, {"from": 1.0, "to": 10.0, "res": 0.1})
        ]

class ACEStepEditWrapper(ACEStepBaseWrapper):
    def __init__(self):
        super().__init__(
            "ACE Audio Repaint (Edit)",
            "Repaint or modify existing audio using ACE-Step.",
            "assets/workflows/ace_step_1_m2m_editing.json"
        )
    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("audio_input", "image", "Input Audio"), # Reusing 'image' type for file picker
            WorkflowWidgetDef("style", "text", "Style", "female vocals, clear"),
            WorkflowWidgetDef("lyrics", "text", "Lyrics", "[ko]\n가사를 수정해보세요."),
            WorkflowWidgetDef("denoise", "slider", "Modification Strength", 0.5, {"from": 0.1, "to": 1.0, "res": 0.01}),
            WorkflowWidgetDef("seed", "slider", "Seed", 0, {"from": 0, "to": 2147483647, "res": 1}),
            WorkflowWidgetDef("steps", "slider", "Steps", 50, {"from": 10, "to": 50, "res": 1}),
            WorkflowWidgetDef("cfg", "slider", "CFG", 5.0, {"from": 1.0, "to": 10.0, "res": 0.1})
        ]

    def apply_values(self, wf, val):
        api = super().apply_values(wf, val)
        if "64" in api: 
            api["64"]["inputs"]["audio"] = val.get("audio_input", "")
        return api

class WorkflowRegistry:
    def __init__(self):
        self._wrappers = {}
        # Register default wrappers
        self.register("z_turbo", ZImageTurboWrapper)
        self.register("ace_instrumental", ACEStepInstrumentalWrapper)
        self.register("ace_song", ACEStepSongWrapper)
        self.register("ace_edit", ACEStepEditWrapper)

    def register(self, key, wrapper_class):
        self._wrappers[key] = wrapper_class()

    def get_all_names(self):
        return [w.name for w in self._wrappers.values()]

    def get_by_key(self, key):
        return self._wrappers.get(key)

    def get_by_name(self, name):
        for w in self._wrappers.values():
            if w.name == name: return w
        return None

# Singleton instance
registry = WorkflowRegistry()
