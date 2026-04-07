"""
Menu Configuration Loader
Loads menu items from config files and applies user overrides.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional

from .paths import ROOT_DIR


class MenuConfig:
    def __init__(self, config_rel_path: str = "config/categories"):
        # Resolve path relative to repo root
        self.root_dir = ROOT_DIR
        self.config_dir = self.root_dir / config_rel_path
            
        self.items: List[Dict] = []
        self._base_items: List[Dict] = []  # Before overrides
        self.load()

    def load(self):
        """
        Loads configuration from config/menu/categories/*.json files
        and applies user overrides.
        """
        if not self.config_dir.exists():
            print(f"[WARN] Config category directory not found: {self.config_dir}")
            self._base_items = []
            self.items = []
            return

        # 1. Load base items from category files
        self._base_items = []
        files = sorted(self.config_dir.glob("*.json"))
        
        for json_file in files:
            try:
                with open(json_file, 'r', encoding='utf-8-sig', errors='replace') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._base_items.extend(data)
                    elif isinstance(data, dict):
                        # Handle dict-based category
                        cat_id = data.get("id", "Unknown")
                        
                        # Support cases where the root dict itself is a feature/item
                        if data.get("id"):
                            self._base_items.append(data)
                            
                        # Handle nested 'features'
                        features = data.get("features", [])
                        if isinstance(features, list):
                            for f_item in features:
                                if f_item.get("id"):
                                    if not f_item.get("category"):
                                        f_item["category"] = cat_id
                                    self._base_items.append(f_item)
            except Exception as e:
                print(f"Error loading {json_file.name}: {e}")
        
        # 2. Apply user overrides
        try:
            from .user_overrides import UserOverrideManager
            override_mgr = UserOverrideManager(self.root_dir)
            self.items = override_mgr.apply_overrides(self._base_items)
        except Exception as e:
            # Fallback: use base items without overrides
            print(f"Warning: Could not apply overrides: {e}")
            self.items = self._base_items.copy()

    def get_base_items(self) -> List[Dict]:
        """Get base items without any overrides applied."""
        return self._base_items.copy()

    def get_items_by_scope(self, scope: str) -> List[Dict]:
        """
        Get items that match the scope (file, folder, or both).
        """
        return [
            item for item in self.items 
            if (item.get('scope') == scope or item.get('scope') == 'both')
        ]

    def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        for item in self.items:
            if item.get('id') == item_id:
                return item
        return None
