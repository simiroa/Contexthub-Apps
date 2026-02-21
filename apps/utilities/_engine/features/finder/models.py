from pathlib import Path
from typing import List
import uuid

class FinderItem:
    """Represents a single file in the finder."""
    def __init__(self, path: Path):
        self.path = path
        self.selected = False
        try:
            self.stat = path.stat()
            self.mtime = self.stat.st_mtime
            self.size = self.stat.st_size
        except:
            self.mtime = 0
            self.size = 0

class FinderGroup:
    """Represents a group of duplicate/similar items."""
    def __init__(self, name: str, items: List[Path]):
        self.name = name
        self.items = [FinderItem(p) for p in items]
        self.id = str(uuid.uuid4()) # Unique ID for UI tracking
        self.total_size = sum(item.size for item in self.items)  # Total size of group
        
        # Determine badge type from name
        self.badge = None # "SEQ", "VER", "HASH"
        self.clean_name = name
        
        if name.startswith("SEQ:"):
            self.badge = "SEQ"
            self.clean_name = name.replace("SEQ:", "").strip()
        elif name.startswith("VER:"):
            self.badge = "VER"
            self.clean_name = name.replace("VER:", "").strip()
        elif name.startswith("HASH:"):
            self.badge = "HASH"
            self.clean_name = name.replace("HASH:", "").strip()

    def select_all(self, state: bool):
        for item in self.items:
            item.selected = state

    def select_by_pattern(self, pattern: str, keep: bool = False) -> int:
        """Selects items matching pattern. Returns count of changes."""
        count = 0
        pattern = pattern.lower()
        for item in self.items:
            path_str = str(item.path).lower()
            match = pattern in path_str
            
            target = False
            if keep:
                # Keep matches -> Select NON-matches
                target = not match
            else:
                # Select matches
                target = match
            
            if item.selected != target:
                item.selected = target
                count += 1
        return count

    def invert_selection(self):
        for item in self.items:
            item.selected = not item.selected

    def mark_all_except_newest(self):
        """Standard 'Keep Newest' logic: Check everything except the newest."""
        if not self.items: return
        best = max(self.items, key=lambda x: x.mtime)
        for item in self.items:
            item.selected = (item != best)

    def mark_all_except_oldest(self):
        """Standard 'Keep Oldest' logic: Check everything except the oldest."""
        if not self.items: return
        best = min(self.items, key=lambda x: x.mtime)
        for item in self.items:
            item.selected = (item != best)
            
    def get_selected_count(self) -> int:
        return sum(1 for i in self.items if i.selected)
