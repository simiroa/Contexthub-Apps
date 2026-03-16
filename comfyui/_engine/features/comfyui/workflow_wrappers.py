from __future__ import annotations

import copy
import random
from abc import ABC, abstractmethod


class WorkflowWidgetDef:
    def __init__(self, key, type, label, default=None, options=None):
        self.key = key
        self.type = type
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
        pass

    @abstractmethod
    def apply_values(self, workflow_json, values):
        pass

    def build_default_workflow(self, values):
        return None


def _parse_resolution(value, fallback=(1024, 1024)):
    if isinstance(value, str) and "x" in value:
        left, right = value.lower().split("x", 1)
        if left.isdigit() and right.isdigit():
            return int(left), int(right)
    return fallback


def _base_txt2img_workflow(values, default_ckpt, default_steps, default_cfg, default_sampler, default_scheduler):
    width, height = _parse_resolution(values.get("resolution"), fallback=(1024, 1024))
    seed = values.get("seed", -1)
    if seed in (-1, None, ""):
        seed = random.randint(1, 2**31 - 1)

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": values.get("ckpt") or default_ckpt},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": values.get("prompt", ""), "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": values.get("negative", ""), "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": int(values.get("batch_size", 1)),
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(seed),
                "steps": int(values.get("steps", default_steps)),
                "cfg": float(values.get("cfg", default_cfg)),
                "sampler_name": values.get("sampler", default_sampler),
                "scheduler": values.get("scheduler", default_scheduler),
                "denoise": float(values.get("denoise", 1.0)),
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": values.get("filename_prefix", "creative_studio"),
                "images": ["6", 0],
            },
        },
    }


class ZImageTurboWrapper(BaseWorkflowWrapper):
    def __init__(self):
        super().__init__(
            "Z-Image Turbo (Fast)",
            "Fast text-to-image preset for iteration and asset blocking.",
            "assets/workflows/z_image/turbo.json",
        )

    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("ckpt", "ckpt", "Checkpoint", "z-image-turbo-fp8-e5m2.safetensors", []),
            WorkflowWidgetDef("prompt", "text", "Positive Prompt", ""),
            WorkflowWidgetDef("negative", "text", "Negative Prompt", "low quality, blurry, text, watermark"),
            WorkflowWidgetDef("resolution", "combo", "Output Size", "1024x1024", ["1024x1024", "896x1152", "1152x896"]),
            WorkflowWidgetDef("steps", "slider", "Steps", 4, {"from": 1, "to": 12, "res": 1}),
            WorkflowWidgetDef("cfg", "slider", "CFG Scale", 2.0, {"from": 1, "to": 8, "res": 0.5}),
            WorkflowWidgetDef("sampler", "combo", "Sampler", "euler", ["euler", "euler_ancestral", "dpmpp_2m"]),
            WorkflowWidgetDef("scheduler", "combo", "Scheduler", "normal", ["normal", "simple", "sgm_uniform"]),
            WorkflowWidgetDef("seed", "seed", "Seed", -1),
            WorkflowWidgetDef("batch_size", "slider", "Batch Size", 1, {"from": 1, "to": 4, "res": 1}),
        ]

    def build_default_workflow(self, values):
        return _base_txt2img_workflow(
            values,
            default_ckpt="z-image-turbo-fp8-e5m2.safetensors",
            default_steps=4,
            default_cfg=2.0,
            default_sampler="euler",
            default_scheduler="normal",
        )

    def apply_values(self, wf, val):
        workflow = copy.deepcopy(wf) if wf else self.build_default_workflow(val)
        if "45" in workflow and "41" in workflow and "44" in workflow:
            workflow["45"]["inputs"]["text"] = val.get("prompt", "")
            workflow["44"]["inputs"]["seed"] = int(val.get("seed", random.randint(1, 2**31 - 1)))
            workflow["44"]["inputs"]["steps"] = int(val.get("steps", 4))
            workflow["44"]["inputs"]["cfg"] = float(val.get("cfg", 2.0))
            width, height = _parse_resolution(val.get("resolution"), fallback=(1024, 1024))
            workflow["41"]["inputs"]["width"] = width
            workflow["41"]["inputs"]["height"] = height
            workflow["41"]["inputs"]["batch_size"] = int(val.get("batch_size", 1))
            return workflow
        return self.build_default_workflow(val)


class SDXLAdvancedWrapper(BaseWorkflowWrapper):
    def __init__(self):
        super().__init__(
            "SDXL Professional (Efficiency)",
            "General-purpose SDXL preset with explicit sampler, negative prompt, and export controls.",
            "assets/workflows/sdxl_advanced.json",
        )

    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("ckpt", "ckpt", "Base Model", "sd_xl_base_1.0.safetensors", []),
            WorkflowWidgetDef("prompt", "text", "Positive Prompt", ""),
            WorkflowWidgetDef("negative", "text", "Negative Prompt", "low quality, blurry, text, watermark"),
            WorkflowWidgetDef("resolution", "combo", "Output Size", "1024x1024", ["1024x1024", "896x1152", "1152x896", "1344x768"]),
            WorkflowWidgetDef("steps", "slider", "Sampling Steps", 24, {"from": 8, "to": 50, "res": 1}),
            WorkflowWidgetDef("cfg", "slider", "CFG Scale", 6.5, {"from": 1, "to": 14, "res": 0.5}),
            WorkflowWidgetDef("sampler", "combo", "Sampler", "dpmpp_2m", ["dpmpp_2m", "euler", "euler_ancestral", "ddim"]),
            WorkflowWidgetDef("scheduler", "combo", "Scheduler", "karras", ["karras", "normal", "sgm_uniform", "simple"]),
            WorkflowWidgetDef("seed", "seed", "Seed", -1),
            WorkflowWidgetDef("batch_size", "slider", "Batch Size", 1, {"from": 1, "to": 4, "res": 1}),
            WorkflowWidgetDef("detailer", "checkbox", "Face Detailer (planned)", False),
        ]

    def build_default_workflow(self, values):
        return _base_txt2img_workflow(
            values,
            default_ckpt="sd_xl_base_1.0.safetensors",
            default_steps=24,
            default_cfg=6.5,
            default_sampler="dpmpp_2m",
            default_scheduler="karras",
        )

    def apply_values(self, wf, val):
        if wf:
            return copy.deepcopy(wf)
        return self.build_default_workflow(val)


class DummyAllWidgetsWrapper(BaseWorkflowWrapper):
    def __init__(self):
        super().__init__(
            "DEBUG: All Widgets (Dummy)",
            "Debug preset for widget coverage and layout tests.",
            "assets/workflows/z_image/turbo.json",
        )

    def get_ui_definition(self):
        return [
            WorkflowWidgetDef("ckpt", "ckpt", "Checkpoint", "sd_xl_base_1.0.safetensors", []),
            WorkflowWidgetDef("prompt", "text", "Prompt Stack", "cinematic concept art"),
            WorkflowWidgetDef("negative", "text", "Negative Prompt", "blurry, bad anatomy"),
            WorkflowWidgetDef("sampler", "combo", "Sampler", "euler", ["euler", "dpmpp_2m", "ddim"]),
            WorkflowWidgetDef("cfg", "slider", "CFG Scale", 7.0, {"from": 1, "to": 20, "res": 0.5}),
            WorkflowWidgetDef("seed", "seed", "Random Seed", -1),
            WorkflowWidgetDef("resolution", "combo", "Aspect / Size", "1024x1024", ["1024x1024", "1216x832"]),
            WorkflowWidgetDef("toggle", "checkbox", "Enable Magic", True),
        ]

    def build_default_workflow(self, values):
        return _base_txt2img_workflow(
            values,
            default_ckpt="sd_xl_base_1.0.safetensors",
            default_steps=18,
            default_cfg=7.0,
            default_sampler="euler",
            default_scheduler="normal",
        )

    def apply_values(self, wf, val):
        return self.build_default_workflow(val)


class WorkflowRegistry:
    def __init__(self):
        self.wrappers = {
            "sdxl_adv": SDXLAdvancedWrapper(),
            "z_turbo": ZImageTurboWrapper(),
            "debug": DummyAllWidgetsWrapper(),
        }

    def get_all_names(self):
        return [w.name for w in self.wrappers.values()]

    def get_by_name(self, name):
        for wrapper in self.wrappers.values():
            if wrapper.name == name:
                return wrapper
        return None
