import json
from pathlib import Path
from datetime import datetime

class LeaveManagerStorage:
    def __init__(self):
        # src/features/leave_manager/storage.py -> src/features -> src -> ContextUp -> userdata
        # Better: use core.paths if available, but relative path fallback is fine for now
        self.userdata_dir = Path(__file__).resolve().parent.parent.parent.parent / "userdata"
        self.data_file = self.userdata_dir / "leave_manager.json"
        
        if not self.userdata_dir.exists():
            self.userdata_dir.mkdir(parents=True, exist_ok=True)
            
        self.default_data = {
            "metadata": {
                "app": "ContextUp Leave Manager",
                "version": "1.0.0",
                "exported_at": ""
            },
            "settings": {
                "reset_date": "01-01",
                "total_days": 15.0,
                "expiration_date": "",
                "leave_types": ["연차", "대체휴가", "병가"]
            },
            "history": [],
            "quotes": [] # Optional, kept for legacy compatibility if needed
        }
        
    def load_data(self):
        if not self.data_file.exists():
            self.save_data(self.default_data)
            return self.default_data
        
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure structure integrity
                if "settings" not in data: data["settings"] = self.default_data["settings"]
                if "history" not in data: data["history"] = []
                if "leave_types" not in data["settings"]: 
                    data["settings"]["leave_types"] = self.default_data["settings"]["leave_types"]
                return data
        except Exception:
            return self.default_data

    def save_data(self, data):
        if "metadata" not in data:
            data["metadata"] = self.default_data["metadata"]
        data["metadata"]["exported_at"] = datetime.now().isoformat()
        
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def export_all_data(self, filepath: str) -> bool:
        """전체 데이터를 JSON 파일로 내보내기"""
        try:
            data = self.load_data()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def import_all_data(self, filepath: str) -> bool:
        """JSON 파일에서 전체 데이터 가져오기"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 기본 구조 검증
            if "settings" in data and "history" in data:
                self.save_data(data)
                return True
            return False
        except Exception:
            return False
