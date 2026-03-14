import sys
from pathlib import Path

# Add shared utils/engine to path
APP_ROOT = Path(__file__).resolve().parent.parent.parent.parent # Apps/ai_lite
_engine_root = APP_ROOT / "_engine"
_feature_root = _engine_root / "features" / "versus_up"

if str(_engine_root) not in sys.path:
    sys.path.insert(0, str(_engine_root))
if str(_feature_root) not in sys.path:
    sys.path.insert(0, str(_feature_root))

from db_handler import DBHandler
from ai_handler import AIHandler
from export_util import ExportUtil

class VersusUpService:
    def __init__(self):
        self.db = DBHandler()
        self.ai = AIHandler()
        
    def get_projects(self):
        return self.db.get_projects()
        
    def create_project(self, name, category, preset_items):
        pid = self.db.create_project(name, category, "")
        for cn, ct, w, d, u in preset_items:
            cid = self.db.add_criterion(pid, cn, ct)
            self.db.update_criterion_settings(cid, w, d, 0, u)
        return pid

    def delete_project(self, pid):
        self.db.delete_project(pid)

    def get_project_data(self, pid):
        products = self.db.get_products(pid)
        criteria = self.db.get_criteria(pid)
        values = self.db.get_values_for_project(pid)
        return products, criteria, values

    def update_value(self, pid, cid, val):
        self.db.update_value(pid, cid, val)

    def add_product(self, pid, name):
        return self.db.add_product(pid, name)

    def delete_product(self, product_id):
        self.db.delete_product(product_id)

    def add_criterion(self, pid, name):
        return self.db.add_criterion(pid, name, "number")

    def delete_criterion(self, cid):
        self.db.delete_criterion(cid)

    def update_criterion_settings(self, cid, name, weight, direction, ignore, unit):
        self.db.update_criterion_name(cid, name)
        self.db.update_criterion_settings(cid, weight, direction, ignore, unit)

    def update_product_image(self, pid, path):
        self.db.update_product_image(pid, path)

    def analyze_images(self, paths, project_name=""):
        return self.ai.analyze_images(paths, project_name)

    def calculate_scores(self, products, criteria, values_map):
        """Ported from legacy update_scores"""
        scores = {p[0]: 0.0 for p in products}
        crit_stats = {}
        
        # 1. Collect valid min/max for normalization
        for cr in criteria:
            cid = cr[0]
            rvs = []
            for p in products:
                raw = values_map.get((p[0], cid), "")
                try: rvs.append(float(raw))
                except: pass
            if rvs: crit_stats[cid] = (min(rvs), max(rvs))

        # 2. Calculate normalized scores
        for cr in criteria:
            cid = cr[0]
            is_ignored = len(cr) > 6 and cr[6]
            if cid in crit_stats and not is_ignored:
                mi, ma = crit_stats[cid]
                direction = cr[5] if len(cr) > 5 else 1
                weight = cr[4]
                
                for p in products:
                    raw = values_map.get((p[0], cid), "")
                    try:
                        fv = float(raw)
                        norm = (fv - mi) / (ma - mi) if ma != mi else 1.0
                        if direction == -1: norm = 1.0 - norm
                        scores[p[0]] += norm * weight
                    except: pass
        return scores, crit_stats

    def export_project(self, project_data, products, criteria, values):
        md = ExportUtil.to_markdown(project_data, products, criteria, values)
        return md
