from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from contexthub.ui.qt.panels import FixedParameterPanel
from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    get_shell_palette,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
    set_button_role,
    set_surface_role,
    set_transparent_surface,
)
from shared._engine.components.icon_button import build_icon_button
from features.video.youtube_downloader_service import DownloadItem, YoutubeDownloaderService

try:
    from PySide6.QtCore import QByteArray, QObject, QSettings, QSize, Qt, QTimer, Signal
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QSizePolicy,
        QScrollArea,
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
    progress = Signal(int, str, float)
    finished = Signal(int, bool, str)
    analyzed = Signal(bool, str)
    thumb_ready = Signal(str)
    engine_updated = Signal(bool, str)


class YoutubeDownloaderWindow(QMainWindow):
    def __init__(self, service: YoutubeDownloaderService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._default_window_size = QSize(650, 920)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._queue_widgets: dict[int, dict[str, QWidget]] = {}
        self._engine_update_started = False

        self.signals = WorkerSignals()
        self.signals.progress.connect(self._on_download_progress)
        self.signals.finished.connect(self._on_download_finished)
        self.signals.analyzed.connect(self._on_analysis_finished)
        self.signals.thumb_ready.connect(self._on_thumb_ready)
        self.signals.engine_updated.connect(self._on_engine_updated)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(self._default_window_size)
        self.setMinimumSize(620, 840)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()
        self._refresh_form()
        self._sync_output_panel()
        self._restore_preview_placeholder()
        self._runtime_timer.start()
        QTimer.singleShot(0, self._on_update_engine_clicked)

        if targets:
            initial_url = next((str(target).strip() for target in targets if str(target).strip()), "")
            if initial_url:
                self.url_edit.setText(initial_url)
                QTimer.singleShot(0, self._on_analyze_clicked)

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        self.header_surface.set_header_visibility(
            show_subtitle=False,
            show_asset_count=False,
            show_runtime_status=False,
        )
        shell_layout.addWidget(self.header_surface)

        self.body_container = QWidget()
        set_surface_role(self.body_container, "content")
        body = QVBoxLayout(self.body_container)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(m.section_gap)

        body.addWidget(self._build_url_card())
        body.addWidget(self._build_preview_card())
        body.addWidget(self._build_download_card())
        body.addWidget(self._build_queue_card())
        shell_layout.addWidget(self.body_container, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _build_url_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(qt_t("youtube_downloader.url_title", "Source URL"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(qt_t("youtube_downloader.url_placeholder", "Paste a video URL and analyze it"))
        self.analyze_btn = build_icon_button(qt_t("youtube_downloader.search_btn", "Analyze"), icon_name="search", role="primary")
        row.addWidget(self.url_edit, 1)
        row.addWidget(self.analyze_btn)
        layout.addLayout(row)
        return card

    def _build_preview_card(self) -> QWidget:
        p = get_shell_palette()
        card = QFrame()
        card.setObjectName("card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(224, 126)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet(f"background: {p.surface_subtle}; border-radius: 10px;")
        layout.addWidget(self.thumb_label, 0)

        info = QVBoxLayout()
        info.setSpacing(6)
        self.video_title_label = QLabel(qt_t("youtube_downloader.title_placeholder", "Analyze a link to inspect the media"))
        self.video_title_label.setObjectName("sectionTitle")
        self.video_title_label.setWordWrap(True)
        self.video_meta_label = QLabel("")
        self.video_meta_label.setObjectName("summaryText")
        self.video_meta_label.setWordWrap(True)
        self.analysis_status_label = QLabel(qt_t("youtube_downloader.status_ready", "Ready"))
        self.analysis_status_label.setObjectName("summaryText")
        self.analysis_status_label.setWordWrap(True)
        info.addWidget(self.video_title_label)
        info.addWidget(self.video_meta_label)
        info.addWidget(self.analysis_status_label)
        info.addStretch(1)
        layout.addLayout(info, 1)
        return card

    def _build_download_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(qt_t("youtube_downloader.export_and_run", "Download"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.param_panel = FixedParameterPanel(
            title="",
            description="",
            preset_label=qt_t("youtube_downloader.format_label", "Format"),
        )
        set_transparent_surface(self.param_panel)
        self.param_panel.setObjectName("downloadOptions")
        self.param_panel.title_label.hide()
        self.param_panel.description_label.hide()
        self.param_panel.preset_combo.addItems(self.service.get_workflow_names())

        self.subs_check = QCheckBox(qt_t("youtube_downloader.subs", "Download subtitles"))
        self.param_panel.add_field("", self.subs_check)
        self.param_panel.layout().setSpacing(8)
        self.subs_check.setContentsMargins(2, 2, 0, 2)
        layout.addWidget(self.param_panel)

        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        output_label = QLabel(qt_t("youtube_downloader.output_dir", "Output"))
        output_label.setObjectName("summaryText")
        output_row.addWidget(output_label, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        output_row.addWidget(self.output_dir_edit, 1)
        self.open_folder_btn = build_icon_button(qt_t("common.open_folder", "Open Folder"), icon_name="folder-open", role="secondary")
        output_row.addWidget(self.open_folder_btn, 0)
        layout.addLayout(output_row)

        self.download_progress = QProgressBar()
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        layout.addWidget(self.download_progress)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.download_status_label = QLabel(qt_t("youtube_downloader.status_ready", "Ready"))
        self.download_status_label.setObjectName("summaryText")
        footer.addWidget(self.download_status_label, 1)
        self.download_btn = build_icon_button(qt_t("youtube_downloader.download_now", "Download"), icon_name="download", role="primary")
        footer.addWidget(self.download_btn, 0)
        layout.addLayout(footer)
        return card

    def _build_queue_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.queue_title_label = QLabel(qt_t("youtube_downloader.downloads", "Queue"))
        self.queue_title_label.setObjectName("sectionTitle")
        self.queue_count_label = QLabel("0")
        self.queue_count_label.setObjectName("summaryText")
        self.clear_queue_btn = build_icon_button(qt_t("common.clear", "Clear"), icon_name="trash-2", role="ghost")
        header.addWidget(self.queue_title_label)
        header.addStretch(1)
        header.addWidget(self.queue_count_label)
        header.addWidget(self.clear_queue_btn)
        layout.addLayout(header)

        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setFrameShape(QFrame.NoFrame)
        self.queue_scroll.setMinimumHeight(84)
        self.queue_scroll.setMaximumHeight(108)
        self.queue_container = QWidget()
        set_surface_role(self.queue_scroll.viewport(), "subtle")
        set_surface_role(self.queue_container, "subtle")
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(10, 10, 10, 10)
        self.queue_layout.setSpacing(8)
        self.queue_layout.addStretch(1)
        self.queue_scroll.setWidget(self.queue_container)
        layout.addWidget(self.queue_scroll)
        return card

    def _bind_actions(self) -> None:
        self.url_edit.returnPressed.connect(self._on_analyze_clicked)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        self.clear_queue_btn.clicked.connect(self._clear_queue)
        self.param_panel.preset_combo.currentTextChanged.connect(self._on_quality_changed)
        self.subs_check.stateChanged.connect(lambda state: self.service.update_parameter("subs", bool(state)))
        self.open_folder_btn.clicked.connect(self.service.reveal_output_dir)
        self.download_btn.clicked.connect(self._on_download_clicked)
        self.output_dir_edit.textChanged.connect(self._sync_output_options)

    def _refresh_form(self) -> None:
        quality = str(self.service.state.parameter_values.get("quality", self.service.get_workflow_names()[0]))
        index = self.param_panel.preset_combo.findText(quality)
        if index >= 0:
            self.param_panel.preset_combo.setCurrentIndex(index)
        self.subs_check.setChecked(bool(self.service.state.parameter_values.get("subs", False)))

    def _sync_output_panel(self) -> None:
        options = self.service.state.output_options
        self.output_dir_edit.setText(str(options.output_dir))

    def _sync_output_options(self) -> None:
        self.service.update_output_options(
            self.output_dir_edit.text(),
            self.service.state.output_options.file_prefix,
            self.service.state.output_options.open_folder_after_run,
            self.service.state.output_options.export_session_json,
        )

    def _restore_preview_placeholder(self) -> None:
        self.thumb_label.setPixmap(QPixmap())
        self.thumb_label.setText(qt_t("youtube_downloader.no_media", "No Media"))

    def _on_quality_changed(self, text: str) -> None:
        self.service.update_parameter("quality", text)

    def _on_analyze_clicked(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            return

        self.analyze_btn.setEnabled(False)
        self.analysis_status_label.setText(qt_t("youtube_downloader.analyzing", "Analyzing..."))
        self.video_title_label.setText(qt_t("youtube_downloader.analyzing_title", "Inspecting media"))
        self.video_meta_label.setText(url)
        self._restore_preview_placeholder()

        def worker() -> None:
            try:
                info = self.service.analyze_url(url)
                thumb_url = str(info.get("thumbnail") or "").strip()
                if thumb_url:
                    b64 = self.service.fetch_thumbnail_base64(thumb_url)
                    if b64:
                        self.signals.thumb_ready.emit(b64)
                self.signals.analyzed.emit(True, "")
            except Exception as exc:
                self.signals.analyzed.emit(False, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_finished(self, success: bool, message: str) -> None:
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText(qt_t("youtube_downloader.search_btn", "Analyze"))
        info = self.service.state.video_info or {}

        if success and info:
            title = str(info.get("title") or qt_t("youtube_downloader.unknown_title", "Unknown title"))
            uploader = str(info.get("uploader") or qt_t("youtube_downloader.unknown_uploader", "Unknown uploader"))
            duration = str(info.get("duration_string") or "??:??")
            extractor = str(info.get("extractor_key") or info.get("extractor") or "")
            self.video_title_label.setText(title)
            meta_parts = [uploader, duration]
            if extractor:
                meta_parts.append(extractor)
            self.video_meta_label.setText(" / ".join(part for part in meta_parts if part))
            self.analysis_status_label.setText(qt_t("youtube_downloader.analysis_ok", "Ready to queue"))
            return

        self.video_title_label.setText(qt_t("youtube_downloader.analysis_failed", "Analysis failed"))
        self.video_meta_label.setText(message)
        self.analysis_status_label.setText(qt_t("youtube_downloader.analysis_retry", "Check the URL or yt-dlp state and try again"))
        self._restore_preview_placeholder()

    def _on_thumb_ready(self, b64: str) -> None:
        pix = QPixmap()
        pix.loadFromData(QByteArray.fromBase64(b64.encode()))
        self.thumb_label.setPixmap(pix.scaled(self.thumb_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.thumb_label.setText("")

    def _on_download_clicked(self) -> None:
        self._sync_output_options()
        item = self.service.add_to_queue()
        if item is None:
            self._set_download_status(qt_t("youtube_downloader.queue_empty", "Analyze a video before downloading"))
            return

        self._add_queue_widget(item)
        self._set_download_status(qt_t("youtube_downloader.queued", "Added to queue"))
        if not self.service.state.is_queue_running:
            threading.Thread(target=self._queue_worker, daemon=True).start()

    def _add_queue_widget(self, item: DownloadItem) -> None:
        widget = QFrame()
        widget.setObjectName("subtlePanel")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel(item.title)
        title.setObjectName("title")
        title.setWordWrap(True)
        status = QLabel(qt_t("youtube_downloader.status_queued", "Queued"))
        status.setObjectName("summaryText")
        header.addWidget(title, 1)
        header.addWidget(status, 0)

        meta = QLabel(f"{item.quality} / {'subs' if item.subs else 'no subs'}")
        meta.setObjectName("summaryText")
        meta.setWordWrap(True)

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setFixedHeight(6)

        layout.addLayout(header)
        layout.addWidget(meta)
        layout.addWidget(progress)
        self.queue_layout.insertWidget(0, widget)
        self._queue_widgets[item.id] = {"widget": widget, "status": status, "progress": progress}
        self._update_queue_summary()

    def _on_download_progress(self, item_id: int, status_text: str, progress: float) -> None:
        widgets = self._queue_widgets.get(item_id)
        if widgets is None:
            return
        widgets["status"].setText(status_text)
        widgets["progress"].setValue(int(progress * 100))
        self.download_progress.setValue(int(progress * 100))
        self._set_download_status(status_text)

    def _on_download_finished(self, item_id: int, success: bool, message: str) -> None:
        widgets = self._queue_widgets.get(item_id)
        if widgets is None:
            return
        widgets["status"].setText(qt_t("youtube_downloader.complete", "Complete") if success else qt_t("youtube_downloader.failed", "Failed"))
        widgets["progress"].setValue(100 if success else 0)
        self.download_progress.setValue(100 if success else 0)
        self._set_download_status(message)

    def _queue_worker(self) -> None:
        self.service.state.is_queue_running = True
        while self.service.state.downloads:
            item = next((entry for entry in self.service.state.downloads if entry.status == "queued"), None)
            if item is None:
                break

            item.status = "starting"
            self.signals.progress.emit(item.id, qt_t("youtube_downloader.status_starting", "Starting..."), 0.0)

            def hook(data: dict) -> None:
                if data.get("status") != "downloading":
                    return
                percent_str = str(data.get("_percent_str") or "0%").strip().replace("%", "")
                try:
                    percent = float(percent_str) / 100.0
                except ValueError:
                    percent = 0.0
                self.signals.progress.emit(item.id, str(data.get("_percent_str") or "0%"), percent)

            try:
                self.service.download_item(item, hook)
                item.status = "complete"
                self.signals.finished.emit(item.id, True, f"Finished: {item.title}")
            except Exception as exc:
                item.status = "failed"
                self.signals.finished.emit(item.id, False, str(exc))

            time.sleep(0.25)

        self.service.state.is_queue_running = False

    def _clear_queue(self) -> None:
        for widgets in self._queue_widgets.values():
            self.queue_layout.removeWidget(widgets["widget"])
            widgets["widget"].deleteLater()
        self._queue_widgets.clear()
        self.service.state.downloads.clear()
        self.download_progress.setValue(0)
        self._set_download_status(qt_t("youtube_downloader.status_ready", "Ready"))
        self._update_queue_summary()

    def _update_queue_summary(self) -> None:
        self.queue_count_label.setText(str(len(self._queue_widgets)))

    def _on_update_engine_clicked(self) -> None:
        if self._engine_update_started:
            return
        self._engine_update_started = True
        self.analysis_status_label.setText(qt_t("youtube_downloader.updating", "Updating downloader engine in background..."))
        self._set_download_status(qt_t("youtube_downloader.updating", "Updating downloader engine in background..."))

        def worker() -> None:
            try:
                self.service.update_engine()
                self.signals.engine_updated.emit(True, qt_t("youtube_downloader.update_ok", "Engine updated"))
            except Exception as exc:
                self.signals.engine_updated.emit(False, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_engine_updated(self, success: bool, message: str) -> None:
        self._set_download_status(message)
        self.analysis_status_label.setText(message if success else qt_t("youtube_downloader.update_failed", "Engine update failed"))

    def _set_download_status(self, text: str) -> None:
        self.download_status_label.setText(text)

    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())
        self._restore_preview_placeholder()

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            if self.width() > self._default_window_size.width() + 40 or self.height() > self._default_window_size.height() + 80:
                restored_pos = self.pos()
                self.resize(self._default_window_size)
                self.move(restored_pos)
        if self._settings.value("is_maximized", False, bool):
            self.showMaximized()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = YoutubeDownloaderWindow(YoutubeDownloaderService(), Path(__file__).resolve().parents[3] / "youtube_downloader", targets)
    window.show()
    return app.exec()
