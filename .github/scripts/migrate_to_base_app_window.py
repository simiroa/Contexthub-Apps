"""Migrate Qt app windows to BaseAppWindow inheritance.

Only edits files where the canonical pattern matches line-for-line.
Reports skipped files for manual review.

Run: python .github/scripts/migrate_to_base_app_window.py <file> [<file> ...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


# Canonical method bodies we are willing to delete (whitespace-normalised match).
CANONICAL_CHECK = """    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())
"""

CANONICAL_CHECK_COMPACT = """    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature: return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())
"""

CANONICAL_RESTORE = """    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        if self._settings.value("is_maximized", False, bool):
            self.showMaximized()
"""

CANONICAL_RESTORE_COMPACT = """    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry: self.restoreGeometry(geometry)
        if self._settings.value("is_maximized", False, bool): self.showMaximized()
"""

CANONICAL_CLOSE = """    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())
        super().closeEvent(event)
"""


def find_app_id(text: str) -> str | None:
    m = re.search(r'^APP_ID\s*=\s*[\'"]([^\'"]+)[\'"]', text, re.MULTILINE)
    return m.group(1) if m else None


def find_main_class(text: str) -> tuple[str, str] | None:
    """Return (class_name, full_bases_string) of the main window class.

    We look for `class X(QMainWindow...):` lines and assume the first one
    that uses QSettings("Contexthub", APP_ID) inside its body is the main
    one. For our scope, this is usually the only QMainWindow subclass per
    file.
    """
    for m in re.finditer(r'^class (\w+)\(([^)]*QMainWindow[^)]*)\):', text, re.MULTILINE):
        return m.group(1), m.group(2)
    return None


def report_skip(path: Path, reason: str) -> None:
    print(f"SKIP {path}: {reason}")


def migrate(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    app_id = find_app_id(text)
    if not app_id:
        report_skip(path, "no module-level APP_ID")
        return False

    main = find_main_class(text)
    if not main:
        report_skip(path, "no class FooWindow(QMainWindow, ...)")
        return False
    class_name, bases = main

    # 1. Change class signature: QMainWindow -> BaseAppWindow, inject APP_ID
    # attribute on the next line.
    new_bases = re.sub(r'\bQMainWindow\b', 'BaseAppWindow', bases)
    new_class_line = f'class {class_name}({new_bases}):\n    APP_ID = "{app_id}"\n'
    text = re.sub(
        rf'^class {re.escape(class_name)}\({re.escape(bases)}\):\n',
        new_class_line,
        text,
        count=1,
        flags=re.MULTILINE,
    )

    # 2. Add BaseAppWindow import if missing.
    if 'from shared._engine.runtime.base_window import BaseAppWindow' not in text:
        # Insert just before the first `from shared._engine.runtime.` import,
        # or after the QMainWindow import block.
        if re.search(r'from shared\._engine\.runtime\.', text):
            text = re.sub(
                r'(from shared\._engine\.runtime\.[^\n]+\n)',
                r'from shared._engine.runtime.base_window import BaseAppWindow\n\1',
                text,
                count=1,
            )
        else:
            # Insert after the first PySide6 widgets import block.
            text = re.sub(
                r'(\nfrom PySide6\.QtWidgets[^\n]+\n)',
                r'\1from shared._engine.runtime.base_window import BaseAppWindow\n',
                text,
                count=1,
            )

    # 3. Replace `super().__init__()` with `super().__init__(app_root)` inside
    # the migrated class. We assume the class accepts an `app_root` parameter
    # (the convention across the repo); skip if not.
    init_match = re.search(
        rf'class {re.escape(class_name)}\([^)]+\):\n    APP_ID = "[^"]+"\n((?:.*\n)*?)    def __init__\(self,\s*[^)]*?app_root[^)]*?\)[^:]*:\n        super\(\)\.__init__\(\)\n',
        text,
    )
    if not init_match:
        report_skip(path, f"{class_name}.__init__ doesn't fit the migrate pattern (no `app_root` param or non-standard super call)")
        return False
    text = re.sub(
        rf'(class {re.escape(class_name)}\([^)]+\):\n    APP_ID = "[^"]+"\n(?:.*\n)*?    def __init__\(self,\s*[^)]*?app_root[^)]*?\)[^:]*:\n)        super\(\)\.__init__\(\)\n',
        r'\1        super().__init__(app_root)\n',
        text,
        count=1,
    )

    # 4. Strip duplicate __init__ lines that BaseAppWindow now owns.
    strip_lines = [
        rf'        self\.app_root = Path\(app_root\)\n',
        rf'        self\._settings = QSettings\("Contexthub", APP_ID\)\n',
        rf'        self\._runtime_signature = runtime_settings_signature\(\)\n',
        rf'        self\._runtime_timer = QTimer\(self\)\n',
        rf'        self\._runtime_timer\.setInterval\(1500\)\n',
        rf'        self\._runtime_timer\.timeout\.connect\(self\._check_runtime_preferences\)\n',
        rf'        self\.setWindowFlags\(Qt\.Window \| Qt\.FramelessWindowHint\)\n',
        rf'        self\.setAttribute\(Qt\.WA_TranslucentBackground, True\)\n',
        rf'        self\.setAcceptDrops\(True\)\n',
        rf'        apply_app_icon\(self, self\.app_root\)\n',
    ]
    for pat in strip_lines:
        text = re.sub(pat, '', text, count=1)

    # 5. Delete the canonical 3 methods. Try both expanded and compact forms.
    deleted_methods = 0
    for canonical in (CANONICAL_CHECK, CANONICAL_CHECK_COMPACT):
        if canonical in text:
            text = text.replace(canonical + "\n", "", 1)
            text = text.replace(canonical, "", 1)
            deleted_methods += 1
            break
    for canonical in (CANONICAL_RESTORE, CANONICAL_RESTORE_COMPACT):
        if canonical in text:
            text = text.replace(canonical + "\n", "", 1)
            text = text.replace(canonical, "", 1)
            deleted_methods += 1
            break
    if CANONICAL_CLOSE in text:
        text = text.replace(CANONICAL_CLOSE + "\n", "", 1)
        text = text.replace(CANONICAL_CLOSE, "", 1)
        deleted_methods += 1

    if deleted_methods < 3:
        report_skip(path, f"only matched {deleted_methods}/3 canonical methods (non-standard divergence) — DRY RUN, no write")
        return False

    if text == original:
        report_skip(path, "no changes computed")
        return False

    path.write_text(text, encoding="utf-8")
    print(f"OK   {path}  (APP_ID={app_id}, methods_deleted={deleted_methods})")
    return True


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    ok = 0
    for arg in argv:
        p = Path(arg).resolve()
        if not p.exists():
            print(f"SKIP {p}: not found")
            continue
        if migrate(p):
            ok += 1
    print(f"\n{ok}/{len(argv)} migrated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
