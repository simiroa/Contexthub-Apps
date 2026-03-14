"""
Audit dependencies and GUI flags for ContextUp features.
"""
import os
import re
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
SRC_DIR = BASE_DIR / "src"
CAT_DIR = BASE_DIR / "config" / "categories"

# Mapping from menu.py (manual extraction for speed/safety)
HANDLER_MAP = {
    "image_convert": "features/image/convert_gui.py",
    "merge_to_exr": "features/image/merge_exr.py",
    "resize_power_of_2": "features/image/resize_gui.py",
    "split_exr": "features/image/split_exr.py",
    "texture_packer_orm": "features/image/packer_gui.py",
    "normal_flip_green": "features/image/normal.py",
    "simple_normal_roughness": "features/image/normal.py",
    "rife_interpolation": "features/ai/frame_interp.py",
    "whisper_subtitle": "features/ai/subtitle.py",
    "esrgan_upscale": "features/image/upscale.py",
    "rmbg_background": "features/ai/tools.py",
    "marigold_pbr": "features/ai/marigold_gui.py",
    "gemini_image_tool": "features/ai/standalone/gemini_img_tools.py",
    "demucs_stems": "features/audio/separate_gui.py",
    "video_convert": "features/video/tools.py",
    "extract_audio": "features/video/tools.py",
    "interpolate_30fps": "features/video/tools.py",
    "create_proxy": "features/video/tools.py",
    "remove_audio": "features/video/tools.py",
    "sequence_to_video": "features/video/tools.py",
    "sequence_analyze": "features/video/sequence_analyze.py",
    "audio_convert": "features/audio/convert_gui.py",
    "extract_bgm": "features/audio/separate_gui.py",
    "extract_voice": "features/audio/separate_gui.py",
    "normalize_volume": "features/audio/tools.py",
    "clean_empty_folders": "features/system/tools.py",
    "move_to_new_folder": "features/system/tools.py",
    "unwrap_folder": "features/system/unwrap_folder_gui.py",
    "finder": "features/finder.py",
    "create_symlink": "features/system/tools.py",
    "auto_lod": "features/mesh/lod_gui.py",
    "cad_to_obj": "features/mesh/mayo.py",
    "mesh_convert": "features/mesh/blender.py",
    "open_with_mayo": "features/mesh/mayo.py",
    "extract_textures": "features/mesh/blender.py",
    "blender_bake_gui": "features/mesh/bake_gui.py",
    "analyze_error": "features/system/clipboard.py",
    "save_clipboard_image": "features/system/tools.py",
    "clipboard_to_new_folder": "features/system/tools.py",
    "copy_unc_path": "features/system/tools.py",
    "doc_convert": "features/document/convert_gui.py",
    "pdf_merge": "features/system/tools.py",
    "pdf_split": "features/system/tools.py",
    "batch_rename": "features/system/rename.py",
    "sequence_renumber": "features/system/rename.py",
    "youtube_downloader": "features/video/downloader_gui.py",
    "vacance": "features/vacance/gui.py",
    "translator": "features/system/translator.py",
    "ai_text_lab": "features/utilities/ai_text_lab.py",
}

# Libraries to track
TRACKED_LIBS = {
    "customtkinter", "Pillow", "requests", "numpy", "cv2", "torch", "yt_dlp", 
    "google-genai", "faster-whisper", "transformers", "kornia", "diffusers", 
    "accelerate", "demucs", "ollama", "openai", "moviepy", "PyPDF2"
}

# Normalize library names (import name -> pip package name)
LIB_MAP = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "Pillow": "Pillow",
    "yt_dlp": "yt-dlp",
    "google": "google-genai",
    "faster_whisper": "faster-whisper",
    "moviepy": "moviepy",
    "PyPDF2": "PyPDF2",
    "win32api": "pywin32",
    "win32con": "pywin32",
}

# Features that should definitely have show_in_tray: true
TRAY_FEATURES = {"ai_text_lab", "translator", "vacance", "copy_my_info", "open_from_clipboard"}

def get_actual_imports(script_path):
    if not script_path.exists():
        # Try as directory if it's a module
        if (script_path.parent / (script_path.stem + ".py")).exists():
           script_path = script_path.parent / (script_path.stem + ".py")
        else:
           return set()
    
    try:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return set()
    
    imports = set()
    lines = content.splitlines()
    for line in lines:
        # Ignore comments
        if line.strip().startswith("#"): continue
        
        # import X
        match = re.search(r'^\s*import\s+([a-zA-Z0-9_-]+)', line)
        if match:
            lib = match.group(1)
            if lib in TRACKED_LIBS or lib in LIB_MAP:
                imports.add(LIB_MAP.get(lib, lib))
        
        # from X import Y
        match = re.search(r'^\s*from\s+([a-zA-Z0-9_-]+)\s+import', line)
        if match:
            lib = match.group(1)
            if lib in TRACKED_LIBS or lib in LIB_MAP:
                imports.add(LIB_MAP.get(lib, lib))

    return imports

def audit():
    results = {}
    
    for json_file in sorted(CAT_DIR.glob("*.json")):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = []
        is_dict = False
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            is_dict = True
            items = data.get("features", [])
            if "id" in data:
                items = [data] + items
        
        file_modified = False
        for item in items:
            item_id = item.get("id")
            if not item_id or item_id not in HANDLER_MAP:
                continue
            
            script_rel = HANDLER_MAP[item_id]
            # Handle dots in module names (e.g. features.ai.frame_interp)
            if "/" not in script_rel and "." in script_rel:
                script_rel = script_rel.replace(".", "/") + ".py"
                
            script_path = SRC_DIR / script_rel
            
            actual_deps = get_actual_imports(script_path)
            
            # Always ensure customtkinter for GUI apps
            is_gui = "_gui" in script_rel or "gui.py" in script_rel or item.get("gui") is True
            if is_gui:
                actual_deps.add("customtkinter")
                if item.get("gui") is not True:
                    item["gui"] = True
                    file_modified = True
            
            current_deps = set(item.get("dependencies", []))
            
            # Special case for yt-dlp vs yt_dlp
            if "yt_dlp" in current_deps:
                current_deps.remove("yt_dlp")
                current_deps.add("yt-dlp")
                file_modified = True

            missing = actual_deps - current_deps
            if missing:
                print(f"[{item_id}] Missing dependencies: {missing}")
                item["dependencies"] = sorted(list(current_deps | missing))
                file_modified = True
            
            # show_in_tray
            if item_id in TRAY_FEATURES:
                if item.get("show_in_tray") is not True:
                    print(f"[{item_id}] Setting show_in_tray to True")
                    item["show_in_tray"] = True
                    file_modified = True
            
        if file_modified:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Saved changes to {json_file.name}")

if __name__ == "__main__":
    audit()
