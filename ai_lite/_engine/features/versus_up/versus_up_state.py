from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class VersusUpState:
    projects: List[tuple] = field(default_factory=list)
    current_project_id: Optional[int] = None
    
    # Active Project Data
    products: List[tuple] = field(default_factory=list)
    criteria: List[tuple] = field(default_factory=list)
    values_map: Dict[Tuple[int, int], str] = field(default_factory=dict)
    
    # Calculated Data
    scores: Dict[int, float] = field(default_factory=dict)
    crit_stats: Dict[int, Tuple[float, float]] = field(default_factory=dict)
    
    # UI State
    sidebar_visible: bool = True
    is_loading: bool = False
    
    def get_current_project_name(self):
        if not self.current_project_id: return "No Project"
        for p in self.projects:
            if p[0] == self.current_project_id: return p[1]
        return "Unknown Project"
