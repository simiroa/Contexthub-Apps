import json
import logging
import os
import shutil
import threading
from pathlib import Path

from utils import paths

logger = logging.getLogger("manager.helpers.requirements")


class RequirementHelper:
    PACKAGE_ALIASES = {
        "google-genai": "google-generativeai",
    }

    DEP_MODEL_MAP = {
        "rembg": "Rembg",
        "diffusers": "Marigold",
        "faster-whisper": "Whisper",
        "demucs": "Demucs",
        "gfpgan": "Upscale",
        "realesrgan": "Upscale",
        "basicsr": "Upscale",
    }

    ITEM_MODEL_MAP = {
        "rmbg_background": ["BiRefNet"],
        "marigold_pbr": ["Marigold"],
        "whisper_subtitle": ["Whisper"],
        "demucs_stems": ["Demucs"],
    }

    ALL_MODEL_KEYS = (
        "Rembg",
        "BiRefNet",
        "Marigold",
        "Whisper",
        "Demucs",
        "Upscale",
    )

    def __init__(self, root_dir: Path, package_manager):
        self.root_dir = Path(root_dir)
        self.package_manager = package_manager
        self._dep_metadata = self._load_dep_metadata()

    def _load_dep_metadata(self) -> dict:
        meta_path = self.root_dir / "config" / "app" / "dependency_metadata.json"
        if not meta_path.exists():
            return {}
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k.lower(): v for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Failed to load dependency metadata: {e}")
            return {}

    def get_critical_packages(self) -> set:
        critical = set()
        for name, meta in self._dep_metadata.items():
            if meta.get("is_critical"):
                critical.add(name.lower())
        for alias, target in self.PACKAGE_ALIASES.items():
            if target in critical:
                critical.add(alias)
        return critical

    def get_missing_packages(self, deps: list, installed_packages: dict | None = None) -> list:
        if not deps:
            return []
        installed = installed_packages if installed_packages is not None else self.package_manager.get_installed_packages()
        missing = []
        seen = set()
        for dep in deps:
            if not dep:
                continue
            key = str(dep).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            installed_key = self.PACKAGE_ALIASES.get(key, key)
            if installed_key not in installed:
                missing.append(key)
        return missing

    def build_dep_metadata(self, deps: list) -> dict:
        metadata = {}
        for dep in deps:
            key = str(dep).strip().lower()
            if not key:
                continue
            meta_key = self.PACKAGE_ALIASES.get(key, key)
            meta = self._dep_metadata.get(meta_key, {})
            if meta:
                metadata[key] = {
                    "pip_name": meta.get("pip_name", key),
                    "install_args": meta.get("install_args", []),
                }
            else:
                metadata[key] = {"pip_name": key, "install_args": []}
        return metadata

    def get_missing_external_tools(self, tools: list) -> list:
        if not tools:
            return []
        _, missing = self.package_manager.check_external_tools(tools)
        return missing

    def get_model_keys_for_item(self, item: dict) -> list:
        model_keys = set()
        item_id = item.get("id")
        if item_id in self.ITEM_MODEL_MAP:
            model_keys.update(self.ITEM_MODEL_MAP[item_id])
        for dep in item.get("dependencies", []):
            key = str(dep).strip().lower()
            model_key = self.DEP_MODEL_MAP.get(key)
            if model_key:
                model_keys.add(model_key)
        return sorted(model_keys)

    def get_missing_models_for_item(self, item: dict) -> list:
        return self.get_missing_models(self.get_model_keys_for_item(item))

    def get_missing_models(self, model_keys: list) -> list:
        missing = []
        for key in model_keys:
            checker = self._model_checks().get(key)
            if not checker:
                missing.append(key)
                continue
            try:
                if not checker():
                    missing.append(key)
            except Exception as e:
                logger.warning(f"Model check failed for {key}: {e}")
                missing.append(key)
        return missing

    def install_models_async(self, model_keys: list, completion_callback=None):
        if not model_keys:
            if completion_callback:
                completion_callback({})
            return

        def run():
            results = {}
            try:
                from setup import download_models
                model_downloaders = {
                    "Rembg": download_models.download_rembg,
                    "BiRefNet": download_models.download_birefnet,
                    "Marigold": download_models.download_marigold,
                    "Whisper": download_models.download_whisper,
                    "Demucs": download_models.download_demucs,
                    "OCR": download_models.download_ocr,
                    "Upscale": download_models.download_upscale,
                }
                for key in model_keys:
                    func = model_downloaders.get(key)
                    if not func:
                        results[key] = False
                        continue
                    try:
                        results[key] = bool(func())
                    except Exception as e:
                        logger.warning(f"Model download failed for {key}: {e}")
                        results[key] = False
            except Exception as e:
                logger.warning(f"Model download failed to start: {e}")
                for key in model_keys:
                    results[key] = False

            if completion_callback:
                completion_callback(results)

        threading.Thread(target=run, daemon=True).start()

    def remove_models_async(self, model_keys: list, completion_callback=None):
        if not model_keys:
            if completion_callback:
                completion_callback({})
            return

        def run():
            results = {}
            for key in model_keys:
                try:
                    results[key] = self._remove_model(key)
                except Exception as e:
                    logger.warning(f"Model cleanup failed for {key}: {e}")
                    results[key] = False

            if completion_callback:
                completion_callback(results)

        threading.Thread(target=run, daemon=True).start()

    def _model_checks(self) -> dict:
        return {
            "Rembg": self._check_rembg,
            "BiRefNet": self._check_birefnet,
            "Marigold": self._check_marigold,
            "Whisper": self._check_whisper,
            "Demucs": self._check_demucs,
            "Upscale": self._check_upscale,
        }

    def _remove_model(self, model_key: str) -> bool:
        removers = {
            "Rembg": self._remove_rembg,
            "BiRefNet": self._remove_birefnet,
            "Marigold": self._remove_marigold,
            "Whisper": self._remove_whisper,
            "Demucs": self._remove_demucs,
            "Upscale": self._remove_upscale,
        }
        remover = removers.get(model_key)
        if not remover:
            return False
        return remover()

    def _remove_path(self, path: Path) -> bool:
        if not path.exists():
            return True
        try:
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
            return True
        except Exception as e:
            logger.warning(f"Failed to remove {path}: {e}")
            return False

    def _remove_rembg(self) -> bool:
        ok = self._remove_path(paths.REMBG_DIR)
        legacy = Path.home() / ".u2net"
        ok = self._remove_path(legacy) and ok
        return ok

    def _remove_birefnet(self) -> bool:
        ok = True
        cache_dirs = []
        hf_home = os.environ.get("HF_HOME")
        if hf_home:
            cache_dirs.append(Path(hf_home) / "hub")
        hub_cache = os.environ.get("HUGGINGFACE_HUB_CACHE")
        if hub_cache:
            cache_dirs.append(Path(hub_cache))
        transformers_cache = os.environ.get("TRANSFORMERS_CACHE")
        if transformers_cache:
            cache_dirs.append(Path(transformers_cache))
        if not cache_dirs:
            cache_dirs.append(Path.home() / ".cache" / "huggingface" / "hub")

        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue
            for match in cache_dir.glob("models--ZhengPeng7--BiRefNet*"):
                ok = self._remove_path(match) and ok
        return ok

    def _remove_marigold(self) -> bool:
        return self._remove_path(paths.MARIGOLD_DIR)

    def _remove_whisper(self) -> bool:
        return self._remove_path(paths.WHISPER_DIR)

    def _remove_demucs(self) -> bool:
        return self._remove_path(paths.DEMUCS_DIR)

    def _remove_upscale(self) -> bool:
        return self._remove_path(Path.home() / ".cache" / "realesrgan")

    def _check_rembg(self) -> bool:
        model_file = paths.REMBG_DIR / "u2net.onnx"
        return model_file.exists()

    def _check_birefnet(self) -> bool:
        cache_dirs = []
        hf_home = os.environ.get("HF_HOME")
        if hf_home:
            cache_dirs.append(Path(hf_home) / "hub")
        hub_cache = os.environ.get("HUGGINGFACE_HUB_CACHE")
        if hub_cache:
            cache_dirs.append(Path(hub_cache))
        transformers_cache = os.environ.get("TRANSFORMERS_CACHE")
        if transformers_cache:
            cache_dirs.append(Path(transformers_cache))
        if not cache_dirs:
            cache_dirs.append(Path.home() / ".cache" / "huggingface" / "hub")

        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue
            matches = list(cache_dir.glob("models--ZhengPeng7--BiRefNet*"))
            if matches:
                return True
        return False

    def _check_marigold(self) -> bool:
        if not paths.MARIGOLD_DIR.exists():
            return False
        return any(paths.MARIGOLD_DIR.glob("models--*"))

    def _check_whisper(self) -> bool:
        if not paths.WHISPER_DIR.exists():
            return False
        return any(paths.WHISPER_DIR.rglob("*.bin"))

    def _check_demucs(self) -> bool:
        if not paths.DEMUCS_DIR.exists():
            return False
        return any(paths.DEMUCS_DIR.rglob("*.th")) or any(paths.DEMUCS_DIR.rglob("*.pt"))

    def _check_upscale(self) -> bool:
        cache_dir = Path.home() / ".cache" / "realesrgan"
        if cache_dir.exists() and any(cache_dir.glob("*.pth")):
            return True
        return False
