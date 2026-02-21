"""
AI-local path definitions scoped to Apps_installed/ai/_engine.
Keeps heavy model caches inside the app folder.
"""
from pathlib import Path
import os

ENGINE_DIR = Path(__file__).resolve().parents[1]
RESOURCES_DIR = ENGINE_DIR / "resources"
AI_MODELS_DIR = RESOURCES_DIR / "ai_models"

MARIGOLD_DIR = AI_MODELS_DIR / "marigold"
WHISPER_DIR = AI_MODELS_DIR / "whisper"
DEMUCS_DIR = AI_MODELS_DIR / "demucs"
REALESRGAN_DIR = AI_MODELS_DIR / "realesrgan"
BIREFNET_DIR = AI_MODELS_DIR / "BiRefNet"


def ensure_dirs() -> None:
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    AI_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    MARIGOLD_DIR.mkdir(parents=True, exist_ok=True)
    WHISPER_DIR.mkdir(parents=True, exist_ok=True)
    DEMUCS_DIR.mkdir(parents=True, exist_ok=True)
    REALESRGAN_DIR.mkdir(parents=True, exist_ok=True)
    BIREFNET_DIR.mkdir(parents=True, exist_ok=True)


def _set_cache_env(var_name: str, value: Path) -> None:
    os.environ.setdefault(var_name, str(value))


def configure_caches() -> None:
    cache_root = RESOURCES_DIR / "cache"
    hf_home = cache_root / "hf"
    hf_cache = hf_home / "hub"
    xdg_cache = cache_root / "xdg"
    torch_home = cache_root / "torch"

    hf_home.mkdir(parents=True, exist_ok=True)
    hf_cache.mkdir(parents=True, exist_ok=True)
    xdg_cache.mkdir(parents=True, exist_ok=True)
    torch_home.mkdir(parents=True, exist_ok=True)

    _set_cache_env("HF_HOME", hf_home)
    _set_cache_env("HUGGINGFACE_HUB_CACHE", hf_cache)
    _set_cache_env("TRANSFORMERS_CACHE", hf_cache)
    _set_cache_env("DIFFUSERS_CACHE", hf_cache / "diffusers")
    _set_cache_env("XDG_CACHE_HOME", xdg_cache)
    _set_cache_env("TORCH_HOME", torch_home)


ensure_dirs()
configure_caches()
