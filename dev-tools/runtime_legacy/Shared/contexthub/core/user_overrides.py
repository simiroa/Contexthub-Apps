"""
User Override Manager
Handles user customizations separate from base config files.
This allows git updates without losing user changes.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from copy import deepcopy

logger = logging.getLogger("core.user_overrides")

# Fields that users can override
OVERRIDABLE_FIELDS = {"enabled", "order", "name", "hotkey", "submenu", "icon"}

# Current override file version
OVERRIDE_VERSION = 1


class UserOverrideManager:
    """
    Manages user customizations in a separate file from base configs.
    
    Base configs (categories/*.json) are git-managed and read-only.
    User changes are stored in user_overrides.json (gitignored).
    """
    
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.override_file = self.root_dir / "userdata" / "user_overrides.json"
        self._cache: Optional[Dict] = None
    
    def load_overrides(self) -> Dict:
        """
        Load user overrides from file.
        Returns empty structure if file doesn't exist.
        """
        if self._cache is not None:
            return self._cache
        
        default = {
            "version": OVERRIDE_VERSION,
            "overrides": {},  # {item_id: {field: value, ...}}
            "hidden": [],     # [item_id, ...] - items user wants hidden
            "custom": []      # [{...full item...}] - user-created items
        }
        
        if not self.override_file.exists():
            self._cache = default
            return default
        
        try:
            with open(self.override_file, 'r', encoding='utf-8-sig', errors='replace') as f:
                data = json.load(f)
            
            # Ensure all required keys exist
            for key in default:
                if key not in data:
                    data[key] = default[key]
            
            self._cache = data
            return data
            
        except Exception as e:
            logger.error(f"Failed to load overrides: {e}")
            self._cache = default
            return default
    
    def save_overrides(self, data: Optional[Dict] = None) -> bool:
        """
        Save user overrides to file.
        If data is None, saves the cached data.
        """
        if data is None:
            data = self._cache
        
        if data is None:
            return False
        
        try:
            # Ensure directory exists
            self.override_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Clean up empty overrides before saving
            if "overrides" in data:
                data["overrides"] = {
                    k: v for k, v in data["overrides"].items()
                    if v  # Remove empty override dicts
                }
            
            with open(self.override_file, 'w', encoding='utf-8-sig') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self._cache = data
            logger.info(f"Saved overrides: {len(data.get('overrides', {}))} items")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save overrides: {e}")
            return False
    
    def apply_overrides(self, base_items: List[Dict]) -> List[Dict]:
        """
        Apply user overrides to base items.
        
        1. Load base items
        2. Apply individual field overrides
        3. Filter out hidden items
        4. Add custom items
        
        Returns new list (doesn't modify input).
        """
        overrides = self.load_overrides()
        result = []
        
        # Apply overrides to base items
        for base_item in base_items:
            item_id = base_item.get("id")
            
            # Skip hidden items
            if item_id in overrides.get("hidden", []):
                continue
            
            # Create a copy to avoid modifying original
            item = deepcopy(base_item)
            
            # Apply field overrides
            if item_id and item_id in overrides.get("overrides", {}):
                item_overrides = overrides["overrides"][item_id]
                for field, value in item_overrides.items():
                    if field in OVERRIDABLE_FIELDS:
                        item[field] = value
            
            result.append(item)
        
        # Add custom items
        for custom_item in overrides.get("custom", []):
            result.append(deepcopy(custom_item))
        
        return result
    
    def extract_overrides(self, base_items: List[Dict], current_items: List[Dict]) -> Dict:
        """
        Compare current items with base items and extract differences.
        
        Returns override data structure ready to save.
        """
        # Create lookup for base items
        base_lookup = {item.get("id"): item for item in base_items if item.get("id")}
        current_lookup = {item.get("id"): item for item in current_items if item.get("id")}
        
        overrides_data = {
            "version": OVERRIDE_VERSION,
            "overrides": {},
            "hidden": [],
            "custom": []
        }
        
        # Find items that were hidden (in base but not in current)
        for item_id in base_lookup:
            if item_id not in current_lookup:
                overrides_data["hidden"].append(item_id)
        
        # Find overrides for existing items
        for item_id, current_item in current_lookup.items():
            if item_id in base_lookup:
                base_item = base_lookup[item_id]
                item_overrides = {}
                
                # Check each overridable field
                for field in OVERRIDABLE_FIELDS:
                    current_val = current_item.get(field)
                    base_val = base_item.get(field)
                    
                    # If different, record the override
                    if current_val != base_val:
                        item_overrides[field] = current_val
                
                if item_overrides:
                    overrides_data["overrides"][item_id] = item_overrides
            else:
                # Item not in base = custom item
                overrides_data["custom"].append(current_item)
        
        return overrides_data
    
    def set_item_override(self, item_id: str, field: str, value: Any):
        """Set a single field override for an item."""
        if field not in OVERRIDABLE_FIELDS:
            logger.warning(f"Field '{field}' is not overridable")
            return
        
        data = self.load_overrides()
        
        if item_id not in data["overrides"]:
            data["overrides"][item_id] = {}
        
        data["overrides"][item_id][field] = value
        self.save_overrides(data)
    
    def hide_item(self, item_id: str):
        """Hide an item (mark as deleted by user)."""
        data = self.load_overrides()
        
        if item_id not in data["hidden"]:
            data["hidden"].append(item_id)
        
        # Also remove any overrides for this item
        if item_id in data["overrides"]:
            del data["overrides"][item_id]
        
        self.save_overrides(data)
    
    def unhide_item(self, item_id: str):
        """Restore a hidden item."""
        data = self.load_overrides()
        
        if item_id in data["hidden"]:
            data["hidden"].remove(item_id)
            self.save_overrides(data)
    
    def get_hidden_items(self) -> List[str]:
        """Get list of hidden item IDs."""
        return self.load_overrides().get("hidden", [])
    
    def add_custom_item(self, item: Dict):
        """Add a user-created custom item."""
        data = self.load_overrides()
        data["custom"].append(item)
        self.save_overrides(data)
    
    def remove_custom_item(self, item_id: str):
        """Remove a custom item by ID."""
        data = self.load_overrides()
        data["custom"] = [i for i in data["custom"] if i.get("id") != item_id]
        self.save_overrides(data)
    
    def clear_item_overrides(self, item_id: str):
        """Clear all overrides for an item (reset to base)."""
        data = self.load_overrides()
        
        if item_id in data["overrides"]:
            del data["overrides"][item_id]
            self.save_overrides(data)
    
    def invalidate_cache(self):
        """Clear cached data to force reload."""
        self._cache = None
