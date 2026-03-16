"""Leave Manager – service layer for Qt."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from features.leave_manager.logic import LeaveManagerCore
from features.leave_manager.storage import LeaveManagerStorage
from features.leave_manager.leave_manager_state import LeaveManagerState


class LeaveManagerService:
    def __init__(self) -> None:
        self.storage = LeaveManagerStorage()
        self.core = LeaveManagerCore(self.storage)
        self.state = LeaveManagerState()
        self._initialize_state()

    def _initialize_state(self) -> None:
        settings = self.core.get_settings()
        self.state.total_days = float(settings.get("total_days", 15.0))
        self.state.reset_date = settings.get("reset_date", "01-01")
        self.state.expiration_date = settings.get("expiration_date", "")
        
        types = self.core.get_leave_types()
        if types:
            self.state.use_type = types[0]
        self.state.add_type = "대체휴가" # Default add type
        
        self.refresh_stats()

    def refresh_stats(self) -> None:
        self.state.stats = self.core.calculate_balance()

    def get_events_for_month(self, year: int, month: int) -> Dict[int, List[Dict[str, Any]]]:
        return self.core.get_events_for_month(year, month)

    def get_leave_types(self) -> List[str]:
        return self.core.get_leave_types()

    def update_preview_dates(self, start_date: str, duration: float) -> None:
        if len(start_date) == 10:
            self.state.preview_dates = self.core.get_preview_dates(start_date, duration)
        else:
            self.state.preview_dates = []

    def update_preview_range(self, start_date_str: str, end_date_str: str) -> float:
        """Updates preview dates based on a start and end date range. 
        Returns the count of workdays in that range.
        """
        try:
            d1 = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            d2 = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if d1 > d2: d1, d2 = d2, d1
            
            all_dates = []
            curr = d1
            while curr <= d2:
                ds = curr.isoformat()
                # Check for holiday or weekend
                hol = self.core.is_public_holiday(curr.year, curr.month, curr.day)
                if curr.weekday() < 5 and not hol:
                    all_dates.append(ds)
                curr += timedelta(days=1)
            
            self.state.preview_dates = all_dates
            # If the user selects a range that only contains weekends, we still show those dates
            # but the amount will be 0.
            return float(len(all_dates))
        except Exception:
            return 0.0

    def submit_use_leave(self, date_str: str, type_name: str, amount: float, note: str) -> bool:
        dates = self.core.get_preview_dates(date_str, amount)
        if not dates:
            return False
            
        whole = int(amount)
        remainder = amount - whole
        for i, ds in enumerate(dates):
            amt = -1.0 if i < whole else (-remainder if remainder > 0 else 0)
            if amt != 0:
                self.core.add_history_item(ds, type_name, amt, note)
        
        self.refresh_stats()
        return True

    def submit_add_credit(self, date_str: str, type_name: str, amount: float, note: str = "Credit Added") -> None:
        self.core.add_history_item(date_str, type_name, amount, note)
        self.refresh_stats()

    def delete_history_item(self, item: Dict[str, Any]) -> None:
        self.core.delete_history_item_by_content(item)
        self.refresh_stats()

    def get_history(self) -> List[Dict[str, Any]]:
        history = self.core.get_history()
        history.sort(key=lambda x: x.get("date", ""), reverse=True)
        return history

    def save_settings(self, total_days: float, reset_date: str, expiration_date: str) -> None:
        self.core.save_settings(
            total_days=total_days,
            reset_date=reset_date,
            expiration_date=expiration_date
        )
        self.state.total_days = total_days
        self.state.reset_date = reset_date
        self.state.expiration_date = expiration_date
        self.refresh_stats()

    def undo(self) -> bool:
        if self.core.undo():
            self.refresh_stats()
            return True
        return False

    def redo(self) -> bool:
        if self.core.redo():
            self.refresh_stats()
            return True
        return False

    def generate_report(self, app_root: Path) -> str | None:
        import datetime
        fname = f"leave_report_{datetime.datetime.now().strftime('%Y%m%d')}.html"
        out_path = app_root / fname
        if self.core.generate_html_report(str(out_path)):
            return str(out_path)
        return None

    def export_data(self, app_root: Path) -> str | None:
        import datetime
        fname = f"leave_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        out_path = app_root / fname
        if self.storage.export_all_data(str(out_path)):
            return str(out_path)
        return None

    def import_data(self, file_path: str) -> bool:
        if self.storage.import_all_data(file_path):
            self._initialize_state()
            return True
        return False
