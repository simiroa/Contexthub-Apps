"""
Manager Localization Helper (JSON-based)
Loads translations from config/i18n/*.json
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger("manager.localization.translations")

class Translator:
    def __init__(self, root_dir: Path, lang="en"):
        self.root_dir = root_dir
        self.i18n_dir = root_dir / "config" / "i18n"
        self.data = {}
        self.lang = lang
        self.load(lang)
        
    def load(self, lang):
        """Load specific language, falling back to 'en' for missing keys."""
        self.lang = lang
        self.data = {}
        
        # 1. Load English (Base)
        en_path = self.i18n_dir / "en.json"
        if en_path.exists():
            try:
                with open(en_path, "r", encoding="utf-8-sig", errors='replace') as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load en.json: {e}")
                
        # 2. Load Target Language (Merge)
        if lang != "en":
            target_path = self.i18n_dir / f"{lang}.json"
            if target_path.exists():
                try:
                    with open(target_path, "r", encoding="utf-8-sig", errors='replace') as f:
                        target_data = json.load(f)
                        self._merge(self.data, target_data)
                        logger.info(f"Loaded translation: {lang}")
                except Exception as e:
                    logger.error(f"Failed to load {lang}.json: {e}")
        
    def _merge(self, base, target):
        """Recursive merge for dicts."""
        for k, v in target.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._merge(base[k], v)
            else:
                base[k] = v
                
    def get(self, key_path):
        """
        Get translation by dot-notation path. 
        e.g. "manager.sidebar.dashboard"
        Fallback: Returns key_path if not found.
        """
        keys = key_path.split(".")
        val = self.data
        try:
            for k in keys:
                val = val[k]
            return val
        except (KeyError, TypeError):
            return key_path # Return key if missing
    
    def __call__(self, key_path):
        return self.get(key_path)
