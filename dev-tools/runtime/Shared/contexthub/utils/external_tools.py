"""
Helper utilities for locating external tools.
"""
import os
import shutil
from pathlib import Path

from core.settings import load_settings

def _get_tools_root():
    """Get the tools directory root."""
    current_dir = Path(__file__).parent.parent.parent
    return current_dir / "tools"

def get_mayo_conv():
    """Get path to mayo-conv.exe."""
    settings = load_settings()
    # Prioritize specialized key, then general MAYO_PATH
    pth = settings.get("MAYO_CONV_PATH") or settings.get("MAYO_PATH")
    if pth and Path(pth).exists():
        if Path(pth).is_dir():
            target = Path(pth) / "mayo-conv.exe"
            if target.exists(): return str(target)
        else:
            return str(pth)

    mayo_path = _get_tools_root() / "mayo" / "mayo-conv.exe"
    if mayo_path.exists():
        return str(mayo_path)
    raise FileNotFoundError(f"Mayo Converter not found at {mayo_path}")

def get_mayo_viewer():
    """Get path to mayo.exe."""
    settings = load_settings()
    # Prioritize specialized key, then general MAYO_PATH
    pth = settings.get("MAYO_VIEWER_PATH") or settings.get("MAYO_PATH")
    if pth and Path(pth).exists():
        if Path(pth).is_dir():
            target = Path(pth) / "mayo.exe"
            if target.exists(): return str(target)
        else:
            return str(pth)

    mayo_path = _get_tools_root() / "mayo" / "mayo.exe"
    if mayo_path.exists():
        return str(mayo_path)
    raise FileNotFoundError(f"Mayo Viewer not found at {mayo_path}")

def get_blender():
    """Get path to blender.exe.
    Searches in: settings, tools folder, Steam, MS Store, Program Files, PATH.
    """
    settings = load_settings()
    if settings.get("BLENDER_PATH") and Path(settings["BLENDER_PATH"]).exists():
        return settings["BLENDER_PATH"]

    # Check tools folder first
    blender_root = _get_tools_root() / "blender"
    for blender_exe in blender_root.rglob("blender.exe"):
        return str(blender_exe)
    
    # Check common installation paths
    common_paths = [
        # Standard Program Files
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blender Foundation",
        # Steam installation
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Steam" / "steamapps" / "common" / "Blender",
        # User local installation
        Path.home() / "AppData" / "Local" / "Blender Foundation",
        # Microsoft Store (WindowsApps)
        Path.home() / "AppData" / "Local" / "Microsoft" / "WindowsApps",
    ]
    
    for base_path in common_paths:
        if base_path.exists():
            for blender_exe in base_path.rglob("blender.exe"):
                return str(blender_exe)
    
    # Fallback to system PATH
    blender_in_path = shutil.which("blender")
    if blender_in_path:
        return blender_in_path
    
    raise FileNotFoundError(
        "Blender가 설치되어 있지 않습니다.\n\n"
        "다음 경로에서 Blender를 찾을 수 없습니다:\n"
        "- tools/blender 폴더\n"
        "- Program Files\n"
        "- Steam\n"
        "- Microsoft Store\n\n"
        "blender.org 에서 Blender를 다운로드하세요."
    )

def get_quadwild():
    """Get path to quadwild.exe."""
    quadwild_path = _get_tools_root() / "quadwild" / "quadwild.exe"
    if quadwild_path.exists():
        return str(quadwild_path)
    raise FileNotFoundError(f"QuadWild not found at {quadwild_path}")

def get_realesrgan():
    """Get path to realesrgan-ncnn-vulkan.exe."""
    # Check resources/bin first (AI binaries)
    ai_bin_path = Path(__file__).parent.parent.parent / "resources" / "bin" / "realesrgan" / "realesrgan-ncnn-vulkan.exe"
    
    # Fallback to tools folder
    realesrgan_path = _get_tools_root() / "realesrgan" / "realesrgan-ncnn-vulkan.exe"
    if realesrgan_path.exists():
        return str(realesrgan_path)
    raise FileNotFoundError(f"RealESRGAN not found. Install via Manager or run dev/scripts/setup_tools.py")

def get_ffmpeg():
    """Get path to ffmpeg.exe."""
    settings = load_settings()
    if settings.get("FFMPEG_PATH") and Path(settings["FFMPEG_PATH"]).exists():
        return settings["FFMPEG_PATH"]

    # Check tools/ffmpeg/bin/ffmpeg.exe
    ffmpeg_path = _get_tools_root() / "ffmpeg" / "bin" / "ffmpeg.exe"
    if ffmpeg_path.exists():
        return str(ffmpeg_path)
    
    # Check tools/ffmpeg/ffmpeg.exe
    ffmpeg_path = _get_tools_root() / "ffmpeg" / "ffmpeg.exe"
    if ffmpeg_path.exists():
        return str(ffmpeg_path)
        
    # Fallback to system path
    return "ffmpeg"

def get_comfyui():
    """Get path to ComfyUI (main.py or run_nvidia_gpu.bat)."""
    settings = load_settings()
    custom = settings.get("COMFYUI_PATH")
    if custom and Path(custom).exists():
        return custom

    # Check tools/ComfyUI
    comfy_root = _get_tools_root() / "ComfyUI"
    if comfy_root.exists():
        # Check for portable version first
        run_bat = comfy_root / "run_nvidia_gpu.bat"
        if run_bat.exists():
            return str(run_bat)
        
        main_py = comfy_root / "main.py"
        if main_py.exists():
            return str(main_py)
            
    return None

