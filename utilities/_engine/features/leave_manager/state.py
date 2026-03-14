"""Leave Manager – application state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class LeaveManagerState:
    selected_date: str = ""
    current_month_year: int = 0        # year
    current_month_month: int = 0       # month (1-12)

    # use-leave tab
    use_type: str = ""
    use_amount: float = 1.0
    use_note: str = ""

    # add-credit tab
    add_type: str = ""
    add_amount: float = 1.0

    # preview
    preview_dates: List[str] = field(default_factory=list)

    # history
    history_expanded: bool = False
    search_query: str = ""
    filter_type: str = "All"

    # stats cache
    stats: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        today = date.today()
        if not self.selected_date:
            self.selected_date = today.isoformat()
        if self.current_month_year == 0:
            self.current_month_year = today.year
        if self.current_month_month == 0:
            self.current_month_month = today.month
