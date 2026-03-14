"""
Internationalization (i18n) Module for ContextUp.

Provides a simple, centralized system for loading and accessing localized strings.
Usage:
    from utils.i18n import t, get_language, set_language

    # Get a translated string
    label_text = t("common.cancel")  # Returns "취소" in Korean, "Cancel" in English

    # With placeholders
    status_text = t("image_convert_gui.convert_n_files", count=5)  # "5개 파일 변환"
"""
import json
import os
import sys
from pathlib import Path
from functools import lru_cache
from typing import Optional, Any, Union
from core.paths import SETTINGS_FILE

# Path to i18n directory relative to this file
I18N_DIR = Path(__file__).parent.parent.parent / "config" / "i18n"
DEFAULT_LANGUAGE = "en"

# Global state - Shared across all module instances to handle double imports
_current_language = DEFAULT_LANGUAGE
if not hasattr(sys, "_contexthub_i18n_strings"):
    sys._contexthub_i18n_strings = {}
_strings: dict = sys._contexthub_i18n_strings
_extra_autoload_done = False


def _get_config_dir() -> Path:
    """Get config directory path."""
    return Path(__file__).parent.parent.parent / "config"


def _load_settings_language() -> str:
    """Load language setting from settings.json, default to 'en'."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                return settings.get("LANGUAGE", DEFAULT_LANGUAGE)
    except Exception:
        pass
    return DEFAULT_LANGUAGE


def _auto_load_extra_strings() -> None:
    """Try loading app-local locales once (for legacy app keys)."""
    global _extra_autoload_done
    if _extra_autoload_done:
        return
    _extra_autoload_done = True

    app_root = os.environ.get("CTX_APP_ROOT")
    if not app_root:
        try:
            app_root = str(Path(sys.argv[0]).resolve().parent)
        except Exception:
            app_root = str(Path.cwd())

    root_path = Path(app_root)
    search_paths: list[Path] = []

    cur = root_path
    for _ in range(4):
        search_paths.append(cur)
        sibling_engine = cur / "_engine"
        if sibling_engine.exists():
            search_paths.append(sibling_engine)
        if cur.parent == cur:
            break
        cur = cur.parent

    for path in reversed(search_paths):
        for name in ("locales.json", "translations.json"):
            loc = path / name
            if not loc.exists():
                continue
            try:
                with open(loc, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                _merge_dicts(_strings, loaded)
            except Exception:
                continue


@lru_cache(maxsize=4)
def _load_language_file(lang: str) -> dict:
    """Load and cache a language file."""
    path = I18N_DIR / f"{lang}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _init():
    """Initialize the i18n system."""
    global _current_language, _strings

    _current_language = _load_settings_language()

    # Ensure _strings is correctly pointing to the shared cache
    if id(_strings) != id(getattr(sys, "_contexthub_i18n_strings", None)):
        _strings = sys._contexthub_i18n_strings

    # Clear and Load English as fallback
    _strings.clear()
    _strings.update(_load_language_file(DEFAULT_LANGUAGE))

    # Overlay with selected language if different
    if _current_language != DEFAULT_LANGUAGE:
        lang_strings = _load_language_file(_current_language)
        _merge_dicts(_strings, lang_strings)


def _merge_dicts(base: dict, overlay: dict):
    """Recursively merge overlay into base."""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _merge_dicts(base[key], value)
        else:
            base[key] = value


def get_language() -> str:
    """Get the current language code."""
    return _current_language


def set_language(lang: str):
    """
    Set the current language and reload strings.

    Args:
        lang: Language code (e.g., 'en', 'ko')
    """
    global _current_language

    # Clear cache
    _load_language_file.cache_clear()

    _current_language = lang
    _init()


def get_available_languages() -> list[dict]:
    """
    Get list of available languages.

    Returns:
        List of dicts with 'code' and 'name' keys
    """
    languages = []
    for path in I18N_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                meta = data.get("_meta", {})
                languages.append({
                    "code": path.stem,
                    "name": meta.get("name", path.stem),
                    "description": meta.get("description", "")
                })
        except Exception:
            pass
    return languages


def t(key: str, default: Optional[str] = None, **kwargs: Any) -> str:
    """
    Get a translated string.

    Args:
        key: Dot-separated key path (e.g., "common.cancel", "image_convert_gui.title")
        default: Default value if key not found (defaults to key itself)
        **kwargs: Placeholder values for string formatting

    Returns:
        Translated string with placeholders filled in

    Example:
        t("common.cancel")  # "Cancel" or "취소"
        t("video_convert_gui.converted_result", success=5, total=10)  # "Converted 5/10 files."
    """
    # Ensure initialized
    if not _strings:
        _init()

    # Navigate the nested structure
    parts = key.split(".")
    value = _strings

    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            _auto_load_extra_strings()
            value = _strings
            found = True
            for retry_part in parts:
                if isinstance(value, dict) and retry_part in value:
                    value = value[retry_part]
                else:
                    found = False
                    break
            if not found:
                return default if default is not None else key
            break

    if not isinstance(value, str):
        return default if default is not None else key

    # Format with kwargs if provided
    if kwargs:
        try:
            # Support both {key} and {count} style placeholders
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value

    return value


def load_extra_strings(path: Union[str, Path]):
    """Load additional translation strings from a file."""
    path = Path(path)
    if path.exists():
        print(f"I18n: Loading extra strings from {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                new_strings = json.load(f)
                if not _strings: # Ensure _strings is initialized before merging
                    _init()
                _merge_dicts(_strings, new_strings)
        except Exception as e:
            print(f"I18n: Failed to load {path}: {e}")


# Alias for convenience
_ = t


# Initialize on module load
_init()


if __name__ == "__main__":
    # Test the i18n system
    print(f"Current language: {get_language()}")
    print(f"Available languages: {get_available_languages()}")
    print()

    # Test translations
    print("Testing English (default):")
    print(f"  common.cancel: {t('common.cancel')}")
    print(f"  common.success: {t('common.success')}")

    print()
    print("Testing with placeholders:")
    print(f"  convert_n_files: {t('image_convert_gui.convert_n_files', count=5)}")
    print(f"  converted_result: {t('video_convert_gui.converted_result', success=3, total=5)}")

    print()
    print("Testing Korean:")
    set_language("ko")
    print(f"  common.cancel: {t('common.cancel')}")
    print(f"  features.ai.marigold_pbr: {t('features.ai.marigold_pbr')}")

def get_localized_name(name_str: str) -> str:
    """
    Parses a name string in the format "English Name (Korean Name)"
    and returns the appropriate name based on the current language.

    Args:
        name_str: The name string, e.g., "ai_text_lab (AI 텍스트 연구소)"

    Returns:
        The localized name.
    """
    import re
    # Check for "Name (Bilingual Name)" pattern
    # Only split if the text in parentheses contains non-ASCII characters (e.g., Korean)
    match = re.match(r"^(.*?)\s*\((.*[^\x00-\x7F].*)\)$", name_str.strip())

    if match:
        eng_name = match.group(1).strip()
        kor_name = match.group(2).strip()

        if get_language() == "ko":
            return kor_name
        return eng_name

    return name_str
