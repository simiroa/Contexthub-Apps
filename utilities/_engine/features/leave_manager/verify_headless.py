import sys
from pathlib import Path
from datetime import date

# Bootstrap path
root = Path("c:/Users/HG/Documents/HG_context_v2/ContextUp/src").resolve()
sys.path.append(str(root))

try:
    from features.vacance.logic import VacanceCore
    from features.vacance.ui_components import VacationTicket, StatsBar
    # Mock storage
    class MockStorage:
        def load_data(self):
            return {
                "settings": {"total_days": 15},
                "history": [
                    {"date": (date.today().replace(year=date.today().year + 1)).isoformat(), "amount": -2.0, "note": "Future Trip", "type": "Annual"}
                ]
            }
        def save_data(self, data): pass

    core = VacanceCore(MockStorage())
    
    # Test Logic
    next_vac = core.get_next_upcoming_vacation()
    assert next_vac is not None, "Should find future vacation"
    assert next_vac["note"] == "Future Trip", "Should match mock data"
    
    preview = core.get_preview_dates("2025-01-01", 3.0)
    assert len(preview) == 3, "Should return 3 preview dates"
    
    print("Logic Verification Passed")

    # Test UI Import (Headless check)
    # We can't instantiate CTk classes easily headless without display, but successful import is good sign.
    print("UI Classes Imported Successfully")
    
except Exception as e:
    print(f"VERIFICATION FAILED: {e}")
    sys.exit(1)
