"""
Config Manager for ContextUp Manager GUI
Handles loading, saving, and managing menu configuration with user overrides.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("manager.core.config")


class ConfigManager:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.categories_dir = root_dir / "config" / "categories"
        self._cache = None
        self._base_cache = None  # Base items (without overrides)
        self._last_load_time = None
        
        # Lazy import to avoid circular dependency
        self._override_mgr = None
    
    def _get_override_manager(self):
        """Get or create override manager."""
        if self._override_mgr is None:
            from core.user_overrides import UserOverrideManager
            self._override_mgr = UserOverrideManager(self.root_dir)
        return self._override_mgr
        
    def load_config(self, force_reload=False) -> list:
        """
        Load menu configuration from menu/categories/*.json files
        with user overrides applied.
        """
        if not force_reload and self._cache is not None:
            # Check if files actually changed on disk
            if not self.is_cache_stale():
                return self._cache

        items = []
        base_items = []
        
        try:
            if not self.categories_dir.exists():
                logger.warning(f"Categories dir not found: {self.categories_dir}")
                return []
                
            files = sorted(self.categories_dir.glob("*.json"))
            for fpath in files:
                try:
                    with open(fpath, "r", encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            base_items.extend(data)
                        elif isinstance(data, dict):
                            cat_id = data.get("id", "Unknown")
                            
                            if data.get("id"):
                                base_items.append(data)
                                
                            features = data.get("features", [])
                            if isinstance(features, list):
                                for f_item in features:
                                    if f_item.get("id"):
                                        if not f_item.get("category"):
                                            f_item["category"] = cat_id
                                        base_items.append(f_item)
                except Exception as e:
                    logger.error(f"Error loading {fpath.name}: {e}")
            
            # Store base items for later comparison
            self._base_cache = base_items
            
            # Apply user overrides
            try:
                override_mgr = self._get_override_manager()
                items = override_mgr.apply_overrides(base_items)
            except Exception as e:
                logger.warning(f"Could not apply overrides: {e}")
                items = base_items.copy()
                    
            self._cache = items
            self._last_load_time = time.time()
            return items
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return []
    
    def get_base_items(self) -> list:
        """Get base items without overrides (for comparison)."""
        if self._base_cache is None:
            self.load_config(force_reload=True)
        return self._base_cache.copy() if self._base_cache else []

    def validate_unique_ids(self, items: list) -> tuple:
        """
        Check for duplicate IDs across all items.
        Returns (is_valid, duplicate_ids).
        """
        seen = {}
        duplicates = []
        for item in items:
            item_id = item.get('id')
            if not item_id:
                continue
            if item_id in seen:
                if item_id not in duplicates:
                    duplicates.append(item_id)
            else:
                seen[item_id] = item
        return (len(duplicates) == 0, duplicates)

    def is_cache_stale(self) -> bool:
        """
        Check if any config file changed since last load.
        Returns True if external changes detected.
        """
        if self._cache is None or self._last_load_time is None:
            return True
        try:
            for fpath in self.categories_dir.glob("*.json"):
                if fpath.stat().st_mtime > self._last_load_time:
                    logger.info(f"External change detected: {fpath.name}")
                    return True
        except Exception as e:
            logger.warning(f"Error checking file timestamps: {e}")
            return True
        return False

    def cleanup_empty_files(self) -> list:
        """
        Remove empty category JSON files.
        Returns list of removed filenames.
        """
        removed = []
        try:
            for fpath in self.categories_dir.glob("*.json"):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if not data or (isinstance(data, list) and len(data) == 0):
                        fpath.unlink()
                        removed.append(fpath.name)
                        logger.info(f"Removed empty file: {fpath.name}")
                except Exception as e:
                    logger.warning(f"Error checking {fpath.name}: {e}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        return removed

    def save_config(self, items: list, settings: dict) -> tuple:
        """
        Save user customizations to user_overrides.json.
        Base files (menu_categories/*.json) are NOT modified.
        
        Returns (success: bool, message: str)
        """
        # 1. Validate unique IDs before saving
        is_valid, duplicates = self.validate_unique_ids(items)
        if not is_valid:
            msg = f"Duplicate IDs found: {', '.join(duplicates)}"
            logger.error(msg)
            return (False, msg)
        
        try:
            # 2. Get base items for comparison
            base_items = self.get_base_items()
            
            # 3. Extract overrides (differences from base)
            override_mgr = self._get_override_manager()
            override_data = override_mgr.extract_overrides(base_items, items)
            
            # 4. Save overrides
            if override_mgr.save_overrides(override_data):
                # 5. Update cache
                self._cache = items
                self._last_load_time = time.time()
                
                # Count changes
                num_overrides = len(override_data.get('overrides', {}))
                num_hidden = len(override_data.get('hidden', []))
                num_custom = len(override_data.get('custom', []))
                
                msg = f"Saved: {num_overrides} overrides, {num_hidden} hidden, {num_custom} custom items."
                logger.info(msg)
                return (True, msg)
            else:
                return (False, "Failed to save overrides file.")
            
        except Exception as e:
            msg = f"Error saving config: {e}"
            logger.error(msg)
            return (False, msg)

    def rename_group(self, items: list, old_name: str, new_name: str) -> int:
        """Rename a submenu group across all items."""
        count = 0
        for item in items:
            if item.get('submenu') == old_name:
                item['submenu'] = new_name
                count += 1
        return count

    def ungroup_items(self, items: list, group_name: str) -> int:
        """Move all items in a group to 'ContextUp' root."""
        count = 0
        for item in items:
            if item.get('submenu') == group_name:
                item['submenu'] = "ContextUp"
                count += 1
        return count
