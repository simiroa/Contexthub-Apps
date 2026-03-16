from __future__ import annotations

import sys
import threading
from pathlib import Path

from contexthub.ui.qt.panels import ExportRunPanel, FixedParameterPanel
from contexthub.ui.qt.shell import (
    HeaderSurface,
    apply_app_icon,
    build_shell_stylesheet,
    build_size_grip,
    get_shell_metrics,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
)
from features.video.youtube_downloader_service import YoutubeDownloaderService

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, Signal, QObject, QByteArray
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QScrollArea,
        QSplitter,
        QVBoxLayout,
        QWidget,
        QProgressBar,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for youtube_downloader.") from exc

APP_ID = "youtube_downloader"
APP_TITLE = qt_t("youtube_downloader.title", "Video Downloader")
APP_SUBTITLE = qt_t("youtube_downloader.subtitle", "Download videos from YouTube and other sites.")


class WorkerSignals(QObject):
    progress = Signal(int, str, float) # item_id, status_text, progress
    finished = Signal(int, bool, str) # item_id, success, message
    analyzed = Signal(bool, str) # success, message
    thumb_ready = Signal(str) # b64


class YoutubeDownloaderWindow(QMainWindow):
    def __init__(self, service: YoutubeDownloaderService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._field_widgets: dict[str, QWidget] = {}
        self._queue_widgets: dict[int, QWidget] = {}
        
        self.signals = WorkerSignals()
        self.signals.progress.connect(self._on_download_progress)
        self.signals.finished.connect(self._on_download_finished)
        self.signals.analyzed.connect(self._on_analysis_finished)
        self.signals.thumb_ready.connect(self._on_thumb_ready)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        self._refresh_all()
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        m = get_shell_metrics()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)
        root.setSpacing(m.section_gap)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        self.queue_count_badge = self.header_surface.asset_count_badge
        self.engine_status_badge = self.header_surface.runtime_status_badge
        self.header_surface.open_webui_btn.setText("↑")
        self.header_surface.open_webui_btn.setToolTip(qt_t("youtube_downloader.update_btn", "Update Engine (yt-dlp)"))
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        
        # --- Left Panel: Analysis & Queue ---
        self.left_panel = QFrame()
        self.left_panel.setObjectName("panel") # or card
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(m.section_gap)
        
        # URL Input Bar
        url_card = QFrame()
        url_card.setObjectName("card")
        url_layout = QHBoxLayout(url_card)
        url_layout.setContentsMargins(12, 12, 12, 12)
        url_layout.setSpacing(8)
        
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(qt_t("youtube_downloader.url_placeholder", "Paste video URL here..."))
        self.analyze_btn = QPushButton(qt_t("youtube_downloader.search_btn", "Analyze"))
        self.analyze_btn.setObjectName("primary")
        url_layout.addWidget(self.url_edit, 1)
        url_layout.addWidget(self.analyze_btn, 0)
        left_layout.addWidget(url_card)
        
        # Preview Card
        self.preview_card = QFrame()
        self.preview_card.setObjectName("card")
        preview_layout = QHBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(16)
        
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(160, 90)
        self.thumb_label.setStyleSheet("background: #0b0d11; border-radius: 4px;")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setText(qt_t("youtube_downloader.no_media", "No Media"))
        
        info_layout = QVBoxLayout()
        self.video_title_label = QLabel(qt_t("youtube_downloader.title_placeholder", "Analyze a link..."))
        self.video_title_label.setObjectName("title")
        self.video_title_label.setWordWrap(True)
        self.video_meta_label = QLabel("")
        self.video_meta_label.setObjectName("muted")
        info_layout.addWidget(self.video_title_label)
        info_layout.addWidget(self.video_meta_label)
        info_layout.addStretch(1)
        
        preview_layout.addWidget(self.thumb_label)
        preview_layout.addLayout(info_layout, 1)
        left_layout.addWidget(self.preview_card)
        
        # Queue Card
        queue_card = QFrame()
        queue_card.setObjectName("card")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(12, 12, 12, 12)
        queue_layout.setSpacing(8)
        
        queue_header = QHBoxLayout()
        queue_title = QLabel(qt_t("youtube_downloader.downloads", "Downloads"))
        queue_title.setObjectName("sectionTitle")
        self.clear_queue_btn = QPushButton(qt_t("common.clear", "Clear"))
        self.clear_queue_btn.setObjectName("pillBtn")
        queue_header.addWidget(queue_title)
        queue_header.addStretch(1)
        queue_header.addWidget(self.clear_queue_btn)
        queue_layout.addLayout(queue_header)
        
        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setFrameShape(QFrame.NoFrame)
        self.queue_container = QWidget()
        self.queue_list_layout = QVBoxLayout(self.queue_container)
        self.queue_list_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_list_layout.setSpacing(6)
        self.queue_list_layout.addStretch(1)
        self.queue_scroll.setWidget(self.queue_container)
        queue_layout.addWidget(self.queue_scroll, 1)
        
        left_layout.addWidget(queue_card, 1)
        
        # --- Right Panel: Settings & Action ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("card")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        right_layout.setSpacing(m.section_gap)

        self.param_panel = FixedParameterPanel(
            title=qt_t("youtube_downloader.parameters", "Settings"),
            description="",
            preset_label=qt_t("youtube_downloader.format_label", "Format"),
        )
        self.param_panel.preset_combo.addItems(self.service.get_workflow_names())
        
        self.export_panel = ExportRunPanel(qt_t("youtube_downloader.export_and_run", "Download"))
        self.export_panel.run_btn.setText(qt_t("youtube_downloader.download_now", "Download Now"))
        self.export_panel.set_values(
            str(self.service.state.output_options.output_dir),
            "yt_dl",
            True,
            False
        )
        self.export_panel.export_session_checkbox.hide() # Not useful for this app
        self.export_panel.set_expanded(True)
        
        right_layout.addWidget(self.param_panel, 1)
        right_layout.addWidget(self.export_panel, 0)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 4)
        
        shell_layout.addWidget(self.splitter, 1)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 2, 0)
        grip_row.addStretch(1)
        self.size_grip = build_size_grip()
        self.size_grip.setParent(self.window_shell)
        grip_row.addWidget(self.size_grip, 0, Qt.AlignRight | Qt.AlignBottom)
        shell_layout.addLayout(grip_row)
        
        root.addWidget(self.window_shell)

    def _bind_actions(self) -> None:
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        self.url_edit.returnPressed.connect(self._on_analyze_clicked)
        self.clear_queue_btn.clicked.connect(self._clear_queue)
        
        self.param_panel.preset_combo.currentTextChanged.connect(self._on_quality_changed)
        self.export_panel.reveal_requested.connect(self.service.reveal_output_dir)
        self.export_panel.run_requested.connect(self._on_download_clicked)
        self.header_surface.open_webui_btn.clicked.connect(self._on_update_engine_clicked)
        self.export_panel.toggle_requested.connect(lambda: self.export_panel.set_expanded(not self.export_panel.details.isVisible()))

    def _refresh_all(self) -> None:
        self.queue_count_badge.setText(f"{len(self.service.state.downloads)} downloads")
        self.engine_status_badge.setText("Ready")
        self._refresh_parameter_form()

    def _refresh_parameter_form(self) -> None:
        self.param_panel.clear_fields()
        # Custom UI definition for subs
        self.subs_check = QCheckBox(qt_t("youtube_downloader.subs", "Download Subtitles"))
        self.subs_check.setChecked(self.service.state.parameter_values.get("subs", False))
        self.subs_check.stateChanged.connect(lambda state: self.service.update_parameter("subs", bool(state)))
        self.param_panel.add_field("", self.subs_check)

    def _on_analyze_clicked(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            return
        
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("...")
        self.video_title_label.setText("Analyzing...")
        
        def worker():
            try:
                info = self.service.analyze_url(url)
                self.signals.analyzed.emit(True, "")
                # Fetch thumb
                thumb_url = info.get("thumbnail")
                if thumb_url:
                    b64 = self.service.fetch_thumbnail_base64(thumb_url)
                    if b64:
                        self.signals.thumb_ready.emit(b64)
            except Exception as e:
                self.signals.analyzed.emit(False, str(e))
                
        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_finished(self, success: bool, message: str) -> None:
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText(qt_t("youtube_downloader.search_btn", "Analyze"))
        
        if success and self.service.state.video_info:
            info = self.service.state.video_info
            self.video_title_label.setText(info.get("title", "Unknown"))
            self.video_meta_label.setText(f"{info.get('uploader', 'Unknown')} | {info.get('duration_string', '??:??')}")
        else:
            self.video_title_label.setText("Analysis failed")
            self.video_meta_label.setText(message)

    def _on_thumb_ready(self, b64: str) -> None:
        pix = QPixmap()
        pix.loadFromData(QByteArray.fromBase64(b64.encode()))
        self.thumb_label.setPixmap(pix.scaled(160, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_quality_changed(self, text: str) -> None:
        self.service.update_parameter("quality", text)

    def _on_download_clicked(self) -> None:
        self._sync_output_options()
        item = self.service.add_to_queue()
        if not item:
            return
        
        self._add_queue_widget(item)
        self.queue_count_badge.setText(f"{len(self.service.state.downloads)} downloads")
        
        if not self.service.state.is_queue_running:
            threading.Thread(target=self._queue_worker, daemon=True).start()

    def _sync_output_options(self) -> None:
        self.service.update_output_options(
            self.export_panel.output_dir_edit.text(),
            self.export_panel.output_prefix_edit.text(),
            self.export_panel.open_folder_checkbox.isChecked(),
            self.export_panel.export_session_checkbox.isChecked(),
        )

    def _add_queue_widget(self, item: DownloadItem) -> None:
        widget = QFrame()
        widget.setObjectName("subtlePanel")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        title_row = QHBoxLayout()
        title = QLabel(item.title)
        title.setObjectName("title")
        title.setStyleSheet("font-size: 11px;")
        status = QLabel(qt_t("youtube_downloader.status_queued", "Queued"))
        status.setObjectName("accent")
        status.setStyleSheet("font-size: 10px;")
        title_row.addWidget(title, 1)
        title_row.addWidget(status, 0)
        
        pbar = QProgressBar()
        pbar.setFixedHeight(4)
        pbar.setRange(0, 100)
        pbar.setValue(0)
        pbar.setTextVisible(False)
        
        meta = QLabel(f"{item.quality} | {'subs' if item.subs else 'no subs'}")
        meta.setObjectName("muted")
        meta.setStyleSheet("font-size: 9px;")
        
        layout.addLayout(title_row)
        layout.addWidget(meta)
        layout.addWidget(pbar)
        
        # Insert at top before the stretch
        self.queue_list_layout.insertWidget(0, widget)
        self._queue_widgets[item.id] = {"widget": widget, "status": status, "pbar": pbar}

    def _on_download_progress(self, item_id: int, status_text: str, progress: float) -> None:
        w = self._queue_widgets.get(item_id)
        if w:
            w["status"].setText(status_text)
            w["pbar"].setValue(int(progress * 100))
            if "downloading" in status_text.lower():
                self.export_panel.progress_bar.setValue(int(progress * 100))

    def _on_download_finished(self, item_id: int, success: bool, message: str) -> None:
        w = self._queue_widgets.get(item_id)
        if w:
            w["status"].setText("Complete" if success else "Failed")
            w["status"].setObjectName("success" if success else "danger")
            w["status"].style().unpolish(w["status"])
            w["status"].style().polish(w["status"])
            w["pbar"].setValue(100 if success else 0)
            self.export_panel.status_label.setText(message)

    def _queue_worker(self) -> None:
        self.service.state.is_queue_running = True
        while self.service.state.downloads:
            # Find next queued
            item = None
            for d in self.service.state.downloads:
                if d.status == "queued":
                    item = d
                    break
            if not item:
                break
            
            item.status = "starting"
            self.signals.progress.emit(item.id, "Starting...", 0)
            
            def hook(data):
                if data.get("status") == "downloading":
                    try:
                        p_str = data.get("_percent_str", "0%").strip().replace("%", "")
                        percent = float(p_str) / 100.0
                        self.signals.progress.emit(item.id, data.get("_percent_str", "0%"), percent)
                    except: pass
            
            try:
                self.service.download_item(item, hook)
                item.status = "complete"
                self.signals.finished.emit(item.id, True, f"Finished: {item.title}")
            except Exception as e:
                item.status = "failed"
                self.signals.finished.emit(item.id, False, str(e))
                
            time.sleep(0.5)
            
        self.service.state.is_queue_running = False

    def _clear_queue(self) -> None:
        for w_data in self._queue_widgets.values():
            self.queue_list_layout.removeWidget(w_data["widget"])
            w_data["widget"].deleteLater()
        self._queue_widgets.clear()
        self.service.state.downloads.clear()
        self.queue_count_badge.setText("0 downloads")

    def _on_update_engine_clicked(self) -> None:
        self.header_surface.open_webui_btn.setEnabled(False)
        self.header_surface.open_webui_btn.setText("Updating...")
        def worker():
            try:
                self.service.update_engine()
                # We could signal success
            except: pass
            finally:
                # Need to signal back to UI thread to enable button
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        if self._settings.value("is_maximized", False, bool):
            self.showMaximized()

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = YoutubeDownloaderWindow(YoutubeDownloaderService(), Path(__file__).resolve().parents[3] / "youtube_downloader", targets)
    window.show()
    return app.exec()
