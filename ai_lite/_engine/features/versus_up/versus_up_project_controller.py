from __future__ import annotations

from pathlib import Path

from features.versus_up.versus_up_service import PROJECT_EXTENSION
from features.versus_up.versus_up_qt_widgets import TemplatePickerDialog, TextEntryDialog

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog, QFileDialog, QListWidgetItem, QMessageBox
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for versus_up.") from exc


def commit_runtime_settings(window) -> None:
    window.service.state.ollama_host = window.server_panel.ollama_host_edit.text().strip() or window.service.state.ollama_host
    window.service.state.vision_model = window.server_panel.vision_model_edit.text().strip() or window.service.state.vision_model
    window.service.state.classifier_model = window.server_panel.classifier_model_edit.text().strip() or window.service.state.classifier_model
    window.service.save_settings()
    window._refresh_server_status()


def new_project(window) -> None:
    dialog = TemplatePickerDialog(window.service.get_template_options(), window)
    if dialog.exec() != dialog.Accepted:
        return
    window.service.create_project_from_template(dialog.selected_template)
    window.service.ensure_project_registered()
    window._refresh_all()


def open_project(window, app_title: str) -> None:
    path, _ = QFileDialog.getOpenFileName(window, app_title, str(window.service.projects_dir), f"VersusUp Project (*{PROJECT_EXTENSION})")
    if not path:
        return
    try:
        window.service.load_project(path)
        window._refresh_all()
    except Exception as exc:
        QMessageBox.critical(window, app_title, str(exc))


def save_project(window, app_title: str) -> None:
    suggested = str(window.service.suggested_project_path())
    path, _ = QFileDialog.getSaveFileName(window, app_title, suggested, f"VersusUp Project (*{PROJECT_EXTENSION})")
    if not path:
        return
    if not path.endswith(PROJECT_EXTENSION):
        path += PROJECT_EXTENSION
    window.service.save_project(path)
    window._refresh_all()


def rename_project(window, app_title: str) -> None:
    dialog = TextEntryDialog("Rename Project", "Enter a clearer project name.", window.service.state.project_meta.name, window)
    if dialog.exec() != QDialog.Accepted:
        return
    try:
        window.service.rename_current_project(dialog.value)
        window._refresh_all()
    except Exception as exc:
        QMessageBox.critical(window, app_title, str(exc))


def duplicate_project(window, app_title: str) -> None:
    suggested = f"{window.service.state.project_meta.name} Copy"
    dialog = TextEntryDialog("Duplicate Project", "Create a backup copy with a new name.", suggested, window)
    if dialog.exec() != QDialog.Accepted:
        return
    try:
        window.service.duplicate_current_project(dialog.value)
        window._refresh_all()
    except Exception as exc:
        QMessageBox.critical(window, app_title, str(exc))


def export_report(window) -> None:
    path = window.service.export_report()
    window.service.state.status_text = f"Exported {path.name}"
    window._refresh_server_status()


def export_project_snapshot(window) -> None:
    path = window.service.build_project_snapshot_json()
    window.service.state.status_text = f"Exported {path.name}"
    window._refresh_server_status()


def save_preset(window, app_title: str) -> None:
    dialog = TextEntryDialog("Save Preset", "Store the current comparison structure as a reusable preset.", window.service.state.project_meta.name, window)
    if dialog.exec() != QDialog.Accepted:
        return
    try:
        window.service.save_current_as_preset(dialog.value)
        window._refresh_all()
    except Exception as exc:
        QMessageBox.critical(window, app_title, str(exc))


def remove_preset(window) -> None:
    item = window.history_panel.preset_list.currentItem()
    if item is None:
        return
    window.service.delete_preset(str(item.data(Qt.UserRole)))
    window._refresh_all()


def open_recent_item(window, item: QListWidgetItem) -> None:
    path = Path(str(item.data(Qt.UserRole)))
    if path.exists():
        window.service.load_project(path)
        window._refresh_all()


def open_preset_item(window, item: QListWidgetItem) -> None:
    preset_id = str(item.data(Qt.UserRole))
    window.service.create_project_from_template(f"preset:{preset_id}")
    window.service.ensure_project_registered()
    window._refresh_all()
