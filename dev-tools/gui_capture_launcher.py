from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PySide6.QtCore import QProcess, Qt
    from PySide6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QPlainTextEdit,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PySide6 is required to run the GUI capture launcher.") from exc


ROOT = Path(__file__).resolve().parent.parent
CAPTURE_SCRIPT = ROOT / "dev-tools" / "capture-python-gui-apps.ps1"
DEFAULT_CATEGORIES = ["3d", "ai", "ai_lite", "audio", "comfyui", "document", "image", "native", "utilities", "video"]
ALL_TEMPLATES = {"full", "compact", "mini", "special", "unknown"}


@dataclass(frozen=True)
class AppEntry:
    category: str
    app_id: str
    title: str
    template: str

    @property
    def manifest_id(self) -> str:
        return f"{self.category}/{self.app_id}"


def load_app_entries() -> list[AppEntry]:
    entries: list[AppEntry] = []
    for category in DEFAULT_CATEGORIES:
        cat_dir = ROOT / category
        if not cat_dir.exists():
            continue
        for manifest_path in sorted(cat_dir.rglob("manifest.json")):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            ui = manifest.get("ui", {}) or {}
            execution = manifest.get("execution", {}) or {}
            runtime = manifest.get("runtime", {}) or {}
            if not ui.get("enabled", True):
                continue
            if not str(execution.get("entry_point", "")).endswith(".py"):
                continue
            category_name = str(runtime.get("category", category))
            app_id = str(manifest.get("id") or manifest_path.parent.name)
            title = str(manifest.get("name") or app_id)
            template = str(ui.get("template") or "")
            entries.append(AppEntry(category_name, app_id, title, template))
    return entries


class LauncherWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GUI Capture Launcher")
        self.resize(1180, 780)
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._append_process_output)
        self._proc.finished.connect(self._on_finished)
        self._current_log: list[str] = []
        self._entries = load_app_entries()
        self._category_buttons: dict[str, QPushButton] = {}
        self._template_buttons: dict[str, QPushButton] = {}
        self._active_categories = set(DEFAULT_CATEGORIES)
        self._active_templates = set(ALL_TEMPLATES)
        self._syncing_tree = False
        self._build_ui()
        self._refresh_counts()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("GUI Capture Launcher")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        self.summary = QLabel("")
        self.summary.setStyleSheet("color: #8fa2b8;")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.summary)
        root.addLayout(header)

        filter_row = QVBoxLayout()
        filter_row.setSpacing(8)
        category_line = QHBoxLayout()
        category_label = QLabel("Categories")
        category_label.setStyleSheet("font-weight: 600;")
        category_line.addWidget(category_label)
        self.category_all_btn = QPushButton("All")
        self.category_all_btn.setCheckable(True)
        self.category_all_btn.setChecked(True)
        self.category_all_btn.clicked.connect(self._show_all_categories)
        category_line.addWidget(self.category_all_btn)
        for category in DEFAULT_CATEGORIES:
            btn = QPushButton(category)
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.clicked.connect(lambda checked, c=category: self._toggle_category(c, checked))
            self._category_buttons[category] = btn
            category_line.addWidget(btn)
        category_line.addStretch(1)
        filter_row.addLayout(category_line)

        template_line = QHBoxLayout()
        template_label = QLabel("Templates")
        template_label.setStyleSheet("font-weight: 600;")
        template_line.addWidget(template_label)
        self.template_all_btn = QPushButton("All")
        self.template_all_btn.setCheckable(True)
        self.template_all_btn.setChecked(True)
        self.template_all_btn.clicked.connect(self._show_all_templates)
        template_line.addWidget(self.template_all_btn)
        for template in ["full", "compact", "mini", "special", "unknown"]:
            btn = QPushButton(template)
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.clicked.connect(lambda checked, t=template: self._toggle_template(t, checked))
            self._template_buttons[template] = btn
            template_line.addWidget(btn)
        template_line.addStretch(1)
        filter_row.addLayout(template_line)
        root.addLayout(filter_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["App", "Template"])
        self.tree.setColumnWidth(0, 420)
        self.tree.setColumnWidth(1, 120)
        self.tree.itemChanged.connect(self._on_tree_item_changed)
        root.addWidget(self.tree, 1)
        self._populate_tree()

        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.clear_all_btn = QPushButton("Clear")
        self.refresh_btn = QPushButton("Refresh")
        self.start_btn = QPushButton("Start Capture")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.clear_all_btn)
        btn_row.addWidget(self.refresh_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        root.addLayout(btn_row)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Capture output will appear here.")
        root.addWidget(self.log, 1)

        self.select_all_btn.clicked.connect(self._select_all)
        self.clear_all_btn.clicked.connect(self._clear_all)
        self.refresh_btn.clicked.connect(self._refresh_tree)
        self.start_btn.clicked.connect(self._start_capture)
        self.stop_btn.clicked.connect(self._stop_capture)

    def _populate_tree(self) -> None:
        self._syncing_tree = True
        self.tree.blockSignals(True)
        self.tree.clear()
        category_items: dict[str, QTreeWidgetItem] = {}
        visible_entries = self._visible_entries()
        for category in DEFAULT_CATEGORIES:
            category_item = QTreeWidgetItem([category, ""])
            category_item.setFlags(
                category_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable
            )
            category_item.setCheckState(0, Qt.Checked if category in self._active_categories else Qt.Unchecked)
            category_items[category] = category_item
            self.tree.addTopLevelItem(category_item)
        for entry in visible_entries:
            category_item = category_items.get(entry.category)
            if category_item is None:
                continue
            child = QTreeWidgetItem([f"{entry.app_id} - {entry.title}", entry.template or "auto"])
            child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            child.setCheckState(0, Qt.Checked if entry.category in self._active_categories else Qt.Unchecked)
            child.setData(0, Qt.UserRole, entry.manifest_id)
            category_item.addChild(child)
        self.tree.expandAll()
        self.tree.blockSignals(False)
        self._syncing_tree = False

    def _visible_entries(self) -> list[AppEntry]:
        categories = self._active_categories or set(DEFAULT_CATEGORIES)
        templates = self._active_templates or {"full", "compact", "mini", "special", "unknown"}
        return [
            entry
            for entry in self._entries
            if entry.category in categories and (entry.template or "unknown") in templates
        ]

    def _refresh_tree(self) -> None:
        self._entries = load_app_entries()
        self._populate_tree()
        self._refresh_counts()
        self._append_line("Refreshed app list.")

    def _refresh_counts(self) -> None:
        self.summary.setText(f"{len(self._visible_entries())}/{len(self._entries)} apps")

    def _apply_filters(self) -> None:
        self._populate_tree()
        self._refresh_counts()

    def _show_all_categories(self) -> None:
        self._active_categories = set(DEFAULT_CATEGORIES)
        for btn in self._category_buttons.values():
            btn.setChecked(True)
        self.category_all_btn.setChecked(True)
        self._apply_filters()

    def _toggle_category(self, category: str, checked: bool) -> None:
        if checked:
            self._active_categories.add(category)
        else:
            self._active_categories.discard(category)
        self.category_all_btn.setChecked(len(self._active_categories) == len(DEFAULT_CATEGORIES))
        self._apply_filters()

    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._syncing_tree or column != 0:
            return
        parent = item if item.parent() is None else item.parent()
        category = str(parent.text(0))
        if category not in DEFAULT_CATEGORIES:
            return
        state = parent.checkState(0)
        if state == Qt.Checked:
            self._active_categories.add(category)
        elif state == Qt.Unchecked:
            self._active_categories.discard(category)
        self.category_all_btn.setChecked(len(self._active_categories) == len(DEFAULT_CATEGORIES))
        if category in self._category_buttons:
            self._category_buttons[category].setChecked(category in self._active_categories)
        self._refresh_counts()

    def _show_all_templates(self) -> None:
        self._active_templates = {"full", "compact", "mini", "special", "unknown"}
        for btn in self._template_buttons.values():
            btn.setChecked(True)
        self.template_all_btn.setChecked(True)
        self._apply_filters()

    def _toggle_template(self, template: str, checked: bool) -> None:
        if checked:
            self._active_templates.add(template)
        else:
            self._active_templates.discard(template)
        self.template_all_btn.setChecked(len(self._active_templates) == len(self._template_buttons))
        self._apply_filters()

    def _select_all(self) -> None:
        self._set_all_check_state(Qt.Checked)

    def _clear_all(self) -> None:
        self._set_all_check_state(Qt.Unchecked)

    def _set_all_check_state(self, state: Qt.CheckState) -> None:
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            parent.setCheckState(0, state)
            for j in range(parent.childCount()):
                parent.child(j).setCheckState(0, state)

    def _selected_apps(self) -> list[str]:
        selected: list[str] = []
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.Checked:
                    selected.append(str(child.data(0, Qt.UserRole)))
        return selected

    def _start_capture(self) -> None:
        if self._proc.state() != QProcess.NotRunning:
            QMessageBox.information(self, "Capture Running", "A capture is already running.")
            return

        apps = self._selected_apps()
        if not apps:
            QMessageBox.warning(self, "No Apps Selected", "Select at least one app.")
            return
        if not CAPTURE_SCRIPT.exists():
            QMessageBox.critical(self, "Missing Script", f"Capture script not found:\n{CAPTURE_SCRIPT}")
            return

        args = [
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(CAPTURE_SCRIPT),
            "-Clean",
            "-OnlyApps",
        ] + apps

        self.log.clear()
        self._current_log.clear()
        self._append_line("Starting capture...")
        self._proc.setProgram("powershell.exe")
        self._proc.setArguments(args)
        self._proc.setWorkingDirectory(str(ROOT))
        self._proc.start()
        if not self._proc.waitForStarted(3000):
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            QMessageBox.critical(self, "Start Failed", "Could not start the capture process.")
            return
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _stop_capture(self) -> None:
        if self._proc.state() == QProcess.NotRunning:
            return
        pid = self._proc.processId()
        if pid:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
        self._proc.kill()
        self._append_line("Stop requested.")

    def _append_process_output(self) -> None:
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            for line in data.splitlines():
                self._append_line(line)

    def _append_line(self, text: str) -> None:
        self._current_log.append(text)
        self.log.appendPlainText(text)

    def _on_finished(self) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        code = self._proc.exitCode()
        self._append_line(f"Capture finished with exit code {code}.")


def main() -> int:
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
