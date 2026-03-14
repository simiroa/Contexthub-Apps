import sqlite3
import os
from pathlib import Path

class DBHandler:
    def __init__(self, db_path=None):
        if db_path is None:
            # 기본적으로 앱 데이터 폴더에 저장 (소스 폴더 오염 방지)
            app_data = Path(os.environ.get("APPDATA", ".")) / "Contexthub" / "VersusUp"
            app_data.mkdir(parents=True, exist_ok=True)
            db_path = app_data / "versus_up.db"
        
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON") # Enable cascading deletes
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 프로젝트 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 제품 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    name TEXT NOT NULL,
                    image_path TEXT,
                    url TEXT,
                    notes TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)
            # 비교 기준 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS criteria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    name TEXT NOT NULL,
                    data_type TEXT CHECK(data_type IN ('text', 'number', 'score')),
                    weight REAL DEFAULT 1.0,
                    direction INTEGER DEFAULT 1, -- 1: Higher is better, -1: Lower is better
                    ignore_scoring INTEGER DEFAULT 0, -- 0: Include, 1: Ignore
                    unit TEXT, -- e.g. $, kg, ms
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)
            # 비교 값 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comparison_values (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    criterion_id INTEGER,
                    value TEXT,
                    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
                    FOREIGN KEY (criterion_id) REFERENCES criteria (id) ON DELETE CASCADE
                )
            """)
            # Migration: Ensure columns exist in older database versions
            try: cursor.execute("ALTER TABLE criteria ADD COLUMN direction INTEGER DEFAULT 1")
            except: pass
            try: cursor.execute("ALTER TABLE criteria ADD COLUMN ignore_scoring INTEGER DEFAULT 0")
            except: pass
            try: cursor.execute("ALTER TABLE criteria ADD COLUMN unit TEXT")
            except: pass
            conn.commit()

    # --- Project CRUD ---
    def create_project(self, name, category, description):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO projects (name, category, description) VALUES (?, ?, ?)", 
                           (name, category, description))
            return cursor.lastrowid

    def get_projects(self, search_query=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if search_query:
                cursor.execute("SELECT * FROM projects WHERE name LIKE ? OR category LIKE ? ORDER BY created_at DESC",
                               (f"%{search_query}%", f"%{search_query}%"))
            else:
                cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
            return cursor.fetchall()

    def delete_project(self, project_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()

    # --- Product CRUD ---
    def add_product(self, project_id, name, image_path=None, url=None, notes=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO products (project_id, name, image_path, url, notes) VALUES (?, ?, ?, ?, ?)",
                           (project_id, name, image_path, url, notes))
            return cursor.lastrowid

    def get_products(self, project_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE project_id = ?", (project_id,))
            return cursor.fetchall()

    def update_product_name(self, product_id, name):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE products SET name = ? WHERE id = ?", (name, product_id))
            conn.commit()

    def delete_product(self, product_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()

    # --- Criteria CRUD ---
    def add_criterion(self, project_id, name, data_type, weight=1.0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO criteria (project_id, name, data_type, weight) VALUES (?, ?, ?, ?)",
                           (project_id, name, data_type, weight))
            return cursor.lastrowid

    def get_criteria(self, project_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM criteria WHERE project_id = ?", (project_id,))
            return cursor.fetchall()

    def update_criterion_name(self, criterion_id, name):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE criteria SET name = ? WHERE id = ?", (name, criterion_id))
            conn.commit()

    def clear_all_data(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM comparison_values")
            cursor.execute("DELETE FROM criteria")
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM projects")
            conn.commit()

    def update_criterion_settings(self, criterion_id, weight, direction, ignore_scoring, unit):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE criteria 
                SET weight = ?, direction = ?, ignore_scoring = ?, unit = ?
                WHERE id = ?
            """, (weight, direction, ignore_scoring, unit, criterion_id))
            conn.commit()

    def update_product_image(self, product_id, image_path):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE products SET image_path = ? WHERE id = ?", (image_path, product_id))
            conn.commit()

    def delete_criterion(self, criterion_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM criteria WHERE id = ?", (criterion_id,))
            conn.commit()

    # --- Values Management ---
    def get_values_for_project(self, project_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id as product_id, c.id as criterion_id, cv.value
                FROM products p
                JOIN criteria c ON p.project_id = c.project_id
                LEFT JOIN comparison_values cv ON p.id = cv.product_id AND c.id = cv.criterion_id
                WHERE p.project_id = ?
            """, (project_id,))
            return cursor.fetchall()

    def update_value(self, product_id, criterion_id, value):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM comparison_values WHERE product_id = ? AND criterion_id = ?",
                           (product_id, criterion_id))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE comparison_values SET value = ? WHERE id = ?", (value, row[0]))
            else:
                cursor.execute("INSERT INTO comparison_values (product_id, criterion_id, value) VALUES (?, ?, ?)",
                               (product_id, criterion_id, value))
            conn.commit()

    def insert_dummy_data(self):
        # Check if already has data
        if self.get_projects():
            return

        pid = self.create_project("Cam Benchmark 2024", "Photography", "Choosing a new mirrorless camera for travel.")
        
        # Criteria
        c1 = self.add_criterion(pid, "Resolution", "number", 1.2)
        c2 = self.add_criterion(pid, "Weight (g)", "number", 1.5)
        c3 = self.add_criterion(pid, "Price ($)", "number", 1.0)
        c4 = self.add_criterion(pid, "Autofocus", "score", 1.3)
        
        # Products
        p1 = self.add_product(pid, "Sony A7C II", notes="Compact and powerful.")
        p2 = self.add_product(pid, "Fujifilm X-T5", notes="Classic dials and great colors.")
        p3 = self.add_product(pid, "Canon R6 II", notes="Excellent ergonomics.")
        
        # Values (Sony)
        self.update_value(p1, c1, "33")
        self.update_value(p1, c2, "514")
        self.update_value(p1, c3, "2199")
        self.update_value(p1, c4, "9.5")
        
        # Values (Fuji)
        self.update_value(p2, c1, "40")
        self.update_value(p2, c2, "557")
        self.update_value(p2, c3, "1699")
        self.update_value(p2, c4, "8.5")
        
        # Values (Canon)
        self.update_value(p3, c1, "24")
        self.update_value(p3, c2, "670")
        self.update_value(p3, c3, "2499")
        self.update_value(p3, c4, "9.0")
