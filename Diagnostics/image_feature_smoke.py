from __future__ import annotations

import json
import threading
import time
from pathlib import Path
import os

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "image" / "_engine"
SHARED = ROOT / "dev-tools" / "runtime" / "Shared" / "contexthub"
OUT_DIR = ROOT / "Diagnostics" / "generated" / "image_feature_smoke"
OUT_DIR.mkdir(parents=True, exist_ok=True)

import sys
os.environ["CTX_SHARED_ROOT"] = str(SHARED)
sys.path.insert(0, str(ENGINE))

from features.image.normal_flip_green.service import NormalFlipService
from features.image.simple_normal_roughness.service import SimplePbrService
from features.image.texture_packer_orm.service import TexturePackerService
from features.image.merge_to_exr.service import ExrMergeService
from features.image.merge_to_exr.state import ChannelConfig
from features.image.vectorizer.service import VectorizerService


def make_test_images() -> dict[str, Path]:
    base = OUT_DIR / "base.png"
    r = OUT_DIR / "occlusion.png"
    g = OUT_DIR / "roughness.png"
    b = OUT_DIR / "metallic.png"

    Image.new("RGB", (128, 96), (120, 180, 240)).save(base)
    Image.new("L", (128, 96), 200).save(r)
    Image.new("L", (128, 96), 80).save(g)
    Image.new("L", (128, 96), 140).save(b)
    return {"base": base, "r": r, "g": g, "b": b}


def run_normal_flip(path: Path) -> dict:
    service = NormalFlipService()
    done = threading.Event()
    result = {"ok": False, "errors": []}

    def on_progress(_p, _s):
        return

    def on_complete(count, errors):
        result["ok"] = count > 0 and not errors
        result["errors"] = errors
        done.set()

    service.flip_green_batch([path], on_progress=on_progress, on_complete=on_complete)
    done.wait(15)
    out = path.parent / f"{path.stem}_flipped{path.suffix}"
    result["output"] = str(out)
    result["exists"] = out.exists()
    result["ok"] = result["ok"] and result["exists"]
    return result


def run_simple_pbr(path: Path) -> dict:
    service = SimplePbrService()
    done = threading.Event()
    result = {"ok": False, "errors": []}

    def on_progress(_p, _s):
        return

    def on_complete(count, errors):
        result["ok"] = count > 0 and not errors
        result["errors"] = errors
        done.set()

    service.run_batch_save(
        files=[path],
        params={
            "normal_strength": 1.0,
            "normal_flip_g": False,
            "roughness_contrast": 1.0,
            "roughness_invert": False,
        },
        mode="Normal",
        on_progress=on_progress,
        on_complete=on_complete,
    )
    done.wait(20)
    out = path.parent / f"{path.stem}_normal.png"
    result["output"] = str(out)
    result["exists"] = out.exists()
    result["ok"] = result["ok"] and result["exists"]
    return result


def run_texture_packer(paths: dict[str, Path]) -> dict:
    service = TexturePackerService()
    done = threading.Event()
    result = {"ok": False, "error": ""}

    def on_complete(success, msg):
        result["ok"] = bool(success)
        if not success:
            result["error"] = str(msg)
        done.set()

    out = OUT_DIR / "packed_orm.png"
    service.pack_textures(
        slots={"r": paths["r"], "g": paths["g"], "b": paths["b"]},
        labels={"r": "Occlusion", "g": "Roughness", "b": "Metallic", "a": ""},
        output_path=out,
        resize_size=(128, 96),
        on_complete=on_complete,
    )
    done.wait(20)
    result["output"] = str(out)
    result["exists"] = out.exists()
    result["ok"] = result["ok"] and result["exists"]
    return result


def run_merge_to_exr(paths: dict[str, Path]) -> dict:
    service = ExrMergeService()
    done = threading.Event()
    result = {"ok": False, "error": "", "skipped": False}

    def on_progress(_p, _s):
        return

    def on_complete(success, msg):
        result["ok"] = bool(success)
        if not success:
            result["error"] = str(msg)
        done.set()

    channels = [
        ChannelConfig(source_file=paths["r"].name, target_name="Occlusion", mode="L"),
        ChannelConfig(source_file=paths["g"].name, target_name="Roughness", mode="L"),
        ChannelConfig(source_file=paths["b"].name, target_name="Metallic", mode="L"),
    ]
    all_files = [paths["r"], paths["g"], paths["b"]]
    service.export_exr(
        base_dir=OUT_DIR,
        channels=channels,
        all_files=all_files,
        on_progress=on_progress,
        on_complete=on_complete,
    )
    done.wait(25)
    out = OUT_DIR / "MultiLayer_Output.exr"
    result["output"] = str(out)
    result["exists"] = out.exists()
    if not result["ok"] and any(token in result["error"].lower() for token in ["openexr", "cv2", "imageio", "no module"]):
        result["skipped"] = True
    result["ok"] = result["ok"] and result["exists"]
    return result


def run_vectorizer(path: Path) -> dict:
    service = VectorizerService()
    done = threading.Event()
    result = {"ok": False, "message": "", "skipped": False}

    layers = service.load_files([path])
    if not layers:
        return {"ok": False, "message": "No layers loaded.", "skipped": True}

    output_dir = OUT_DIR / "vectorized"
    output_dir.mkdir(parents=True, exist_ok=True)

    def on_progress(_p, _s):
        return

    def on_complete(success, message):
        result["ok"] = bool(success)
        result["message"] = str(message)
        done.set()

    service.run_vectorization(
        selected_layers=layers[:1],
        output_dir=output_dir,
        config={"filter_speckle": 4, "color_precision": 6, "corner_threshold": 60},
        options={"remove_bg": False, "gen_jsx": False, "split_paths": False, "use_anchor": False},
        on_progress=on_progress,
        on_complete=on_complete,
    )
    done.wait(30)
    svgs = list(output_dir.glob("*.svg"))
    if not result["ok"] and "vtracer" in result["message"].lower():
        result["skipped"] = True
    result["svg_count"] = len(svgs)
    result["ok"] = result["ok"] and len(svgs) > 0
    return result


def main():
    paths = make_test_images()
    report = {
        "normal_flip_green": run_normal_flip(paths["base"]),
        "simple_normal_roughness": run_simple_pbr(paths["base"]),
        "texture_packer_orm": run_texture_packer(paths),
        "merge_to_exr": run_merge_to_exr(paths),
        "rigreader_vectorizer": run_vectorizer(paths["base"]),
        "timestamp": time.time(),
    }

    report_path = OUT_DIR / "smoke_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
