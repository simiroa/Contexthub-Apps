"""
Centralized path definitions for ContextUp.
Encapsulates directory logic to ensure consistency across modules.
"""
from pathlib import Path
import os
import sys

# Define Project Root (ContextHub/)
# Runtimes/Shared/contexthub/utils/paths.py -> contexthub/utils -> contexthub -> Shared -> Runtimes -> ContextHub
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[3]
RESOURCES_DIR = PROJECT_ROOT / "resources" # Fallback if not category-specific

# Resources
RESOURCES_DIR = PROJECT_ROOT / "resources"
AI_MODELS_DIR = RESOURCES_DIR / "ai_models"
BIN_DIR = RESOURCES_DIR / "bin"

# Standard Model Directories
MARIGOLD_DIR = AI_MODELS_DIR / "marigold"
REMBG_DIR = AI_MODELS_DIR / "u2net" # Rembg uses u2net folder name usually, or we enforce it
WHISPER_DIR = AI_MODELS_DIR / "whisper"
DEMUCS_DIR = AI_MODELS_DIR / "demucs"
QWEN_TTS_DIR = AI_MODELS_DIR / "qwen3_tts"

def ensure_dirs():
    """Ensure all critical directories exist."""
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    AI_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)

# Auto-ensure on import
ensure_dirs()
