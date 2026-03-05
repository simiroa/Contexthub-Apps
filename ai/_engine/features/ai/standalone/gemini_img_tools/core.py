"""
Gemini Image Tools - Core Module
Contains API client, utility functions, and common imports.
"""
import sys
import os
import cv2
import numpy as np
from pathlib import Path
import time
import json

# Setup path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(src_dir))

# Logger
from utils.logger import setup_logger
logger = setup_logger("GeminiImageTools")

# Gemini API
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"google-genai not available: {e}")
    genai = None
    types = None
    GENAI_AVAILABLE = False

# Local imports
try:
    from core.settings import load_settings
except ImportError:
    def load_settings():
        return {}


def get_gemini_client():
    """
    Get Gemini API client with proper error handling.
    Checks: environment variables -> config file -> provides user guidance.
    
    Returns:
        tuple: (client, error_message) - client is None if failed
    """
    if not GENAI_AVAILABLE:
        return None, "Google GenAI 라이브러리를 불러올 수 없습니다.\npip install google-genai 를 실행해주세요."
    
    api_key = None
    
    # 1. Check environment variables first (highest priority)
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    
    # 2. Check config file
    if not api_key:
        try:
            settings = load_settings()
            api_key = settings.get('GEMINI_API_KEY') or settings.get('GOOGLE_API_KEY')
        except Exception as e:
            logger.warning(f"Failed to load settings: {e}")
    
    # 3. Check api_keys.json file (legacy support)
    if not api_key:
        try:
            config_path = current_dir.parent.parent.parent.parent / "config" / "api_keys.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    keys = json.load(f)
                    api_key = keys.get('gemini_api_key') or keys.get('google_api_key')
        except Exception as e:
            logger.warning(f"Failed to load api_keys.json: {e}")
    
    if not api_key:
        error_msg = (
            "Gemini API 키가 설정되지 않았습니다.\n\n"
            "설정 방법:\n"
            "1. Google AI Studio에서 API 키 발급:\n"
            "   https://aistudio.google.com/apikey\n\n"
            "2. 다음 중 하나의 방법으로 설정:\n"
            "   A) Manager → Settings → API Key 입력\n"
            "   B) 환경 변수: GEMINI_API_KEY\n"
            "   C) config/api_keys.json 파일 생성"
        )
        return None, error_msg
    
    try:
        client = genai.Client(api_key=api_key)
        return client, None
    except Exception as e:
        error_msg = f"Gemini 클라이언트 생성 실패:\n{e}"
        logger.error(error_msg)
        return None, error_msg


def imread_unicode(path):
    """Reads an image from a path that may contain non-ASCII characters."""
    try:
        stream = np.fromfile(str(path), np.uint8)
        return cv2.imdecode(stream, cv2.IMREAD_COLOR)
    except Exception as e:
        logger.error(f"imread_unicode failed for {path}: {e}")
        return None


def get_unique_path(path: Path) -> Path:
    """Returns a unique path by appending a counter if the file already exists."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    counter = 1
    while True:
        new_path = parent / f"{stem}_{counter:02d}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1
