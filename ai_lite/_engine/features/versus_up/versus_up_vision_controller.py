from __future__ import annotations

from features.versus_up.versus_up_qt_widgets import ProposalReviewDialog, VisionWorker

try:
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import QFileDialog, QMessageBox
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for versus_up.") from exc


def attach_image(window) -> None:
    product = window._selected_product()
    if product is None:
        return
    attach_image_for(window, product.id)


def attach_image_for(window, product_id: str) -> None:
    paths, _ = QFileDialog.getOpenFileNames(window, "Attach Images", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
    if paths:
        window.service.attach_product_images(product_id, paths)
        window.service.state.selected_product_id = product_id
        window._refresh_all()


def select_gallery_image(window, item) -> None:
    product = window._selected_product()
    if product is None:
        return
    sender = window.sender()
    image_path = sender.property("imagePath") if sender is not None else ""
    if image_path:
        window.service.set_main_product_image(product.id, str(image_path))
        window._refresh_all()


def remove_selected_product_image(window) -> None:
    product = window._selected_product()
    if product is None or not product.image_path:
        return
    image_path = product.image_path
    if image_path:
        window.service.remove_product_image(product.id, image_path)
        window._refresh_all()


def run_selected_product_vision(window) -> None:
    product = window._selected_product()
    if product is None:
        return
    window._vision_focus_product_id = product.id
    criterion = window._selected_criterion()
    window._vision_focus_criterion_id = criterion.id if criterion else None
    refresh_vision_panel(window)
    window._open_vision_dialog()


def run_product_vision(window, product_id: str) -> None:
    window.service.state.selected_product_id = product_id
    window._vision_focus_product_id = product_id
    criterion = window._selected_criterion()
    window._vision_focus_criterion_id = criterion.id if criterion else None
    refresh_vision_panel(window)
    window._open_vision_dialog()


def start_vision_thread(window, product_id: str) -> None:
    if product_id in window._vision_threads:
        return
    thread = QThread(window)
    worker = VisionWorker(window.service, product_id)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(window._on_vision_finished)
    worker.failed.connect(window._on_vision_failed)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(lambda pid=product_id: window._cleanup_vision_thread(pid))
    window._vision_threads[product_id] = (thread, worker)
    thread.start()


def cleanup_vision_thread(window, product_id: str) -> None:
    thread_worker = window._vision_threads.pop(product_id, None)
    if thread_worker:
        thread, worker = thread_worker
        worker.deleteLater()
        thread.deleteLater()
    window._rebuild_matrix()
    refresh_vision_panel(window)


def on_vision_finished(window, product_id: str, _cache) -> None:
    window._refresh_all()
    if window._vision_focus_product_id == product_id:
        refresh_vision_panel(window)


def on_vision_failed(window, product_id: str, message: str) -> None:
    window._refresh_all()
    if window._vision_focus_product_id == product_id:
        refresh_vision_panel(window, fallback_error=message)


def review_popup_product(window, app_title: str) -> None:
    product_id = window._vision_focus_product_id or window.service.state.selected_product_id
    if product_id is None:
        return
    product = window.service.product_by_id(product_id)
    if product is None:
        return
    dialog = ProposalReviewDialog(product.vision_cache.proposals, window)
    if dialog.exec() != dialog.Accepted:
        return
    proposals = dialog.approved_proposals()
    applied = window.service.apply_vision_proposals(product.id, proposals)
    window._refresh_all()
    refresh_vision_panel(window)
    QMessageBox.information(window, app_title, "\n".join(applied) if applied else "No proposal was applied.")


def attach_image_for_focus(window) -> None:
    product_id = window._vision_focus_product_id or window.service.state.selected_product_id
    if product_id is None:
        return
    attach_image_for(window, product_id)
    refresh_vision_panel(window)


def run_vision_for_focus(window) -> None:
    product_id = window._vision_focus_product_id or window.service.state.selected_product_id
    if product_id is None:
        return
    product = window.service.product_by_id(product_id)
    if product is None:
        return
    window._vision_focus_product_id = product_id
    refresh_vision_panel(window, loading=True)
    if not product.image_path:
        return
    if product.vision_cache.status == "ready" and product.vision_cache.image_hash:
        refresh_vision_panel(window)
        return
    start_vision_thread(window, product_id)
    window._rebuild_matrix()


def refresh_vision_panel(window, *, loading: bool = False, fallback_error: str = "") -> None:
    panel = window.vision_panel
    product = window.service.product_by_id(window._vision_focus_product_id) if window._vision_focus_product_id else window._selected_product()
    criterion = window.service.criterion_by_id(window._vision_focus_criterion_id) if window._vision_focus_criterion_id else window._selected_criterion()
    product_name = product.name if product else "-"
    criterion_name = criterion.label if criterion else "-"
    cell_value = window.service.cell_value(product.id, criterion.id) if product and criterion else ""
    panel.context_label.setText(f"Focus: {product_name} / {criterion_name}")
    meta_parts = []
    if product:
        meta_parts.append("Image attached" if product.image_path else "No image attached")
    if cell_value:
        meta_parts.append(f"Current cell: {cell_value}")
    if criterion and criterion.description.strip():
        meta_parts.append(criterion.description.strip())
    panel.meta_label.setText(" | ".join(meta_parts) if meta_parts else "Select a product cell to open AI Vision.")
    panel.attach_image_btn.setEnabled(product is not None)
    panel.run_btn.setEnabled(product is not None)
    if product is None:
        panel.status_label.setText("No product selected")
        panel.summary_label.setText("Hover a matrix cell and press AI, or open Cell Detail and select a product.")
        panel.raw_text_label.setText("")
        panel.review_btn.setEnabled(False)
        return
    if loading:
        panel.status_label.setText("Analyzing screenshot with Ollama Vision...")
        panel.summary_label.setText("Vision is extracting OCR/VQA hints for this product.")
        panel.raw_text_label.setText("")
        panel.review_btn.setEnabled(False)
        return
    if not product.image_path:
        panel.status_label.setText("Image required")
        panel.summary_label.setText("Attach a product screenshot first, then run Vision.")
        panel.raw_text_label.setText("")
        panel.review_btn.setEnabled(False)
        return
    if fallback_error or (product.vision_status == "error" and product.vision_cache.error):
        error = fallback_error or product.vision_cache.error
        panel.status_label.setText("Vision failed")
        panel.summary_label.setText(error)
        panel.raw_text_label.setText("")
        panel.review_btn.setEnabled(False)
        return
    if product_id_in_progress(window, product.id):
        panel.status_label.setText("Vision running")
        panel.summary_label.setText("OCR/VQA request is still processing.")
        panel.raw_text_label.setText("")
        panel.review_btn.setEnabled(False)
        return
    if product.vision_cache.status == "ready" and product.vision_cache.image_hash:
        panel.status_label.setText("Vision ready")
        panel.summary_label.setText(product.vision_cache.summary or "No summary returned.")
        raw = product.vision_cache.raw_text.strip()
        panel.raw_text_label.setText(raw[:320] + ("..." if len(raw) > 320 else ""))
        panel.review_btn.setEnabled(bool(product.vision_cache.proposals))
        return
    panel.status_label.setText("Ready to run")
    panel.summary_label.setText("Run Vision to analyze the selected product screenshot.")
    panel.raw_text_label.setText("")
    panel.review_btn.setEnabled(False)


def product_id_in_progress(window, product_id: str) -> bool:
    return product_id in window._vision_threads
