from __future__ import annotations

from features.versus_up.versus_up_qt_widgets import ProposalReviewDialog, VisionWorker

try:
    from PySide6.QtCore import QPoint, QThread
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
    run_product_vision(window, product.id)


def run_product_vision(window, product_id: str) -> None:
    card = window._product_header_cards.get(product_id)
    point = card.mapToGlobal(card.rect().center()) if card is not None else QPoint(0, 0)
    window.service.state.selected_product_id = product_id
    on_product_hovered(window, product_id, point)


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


def on_product_hovered(window, product_id: str, global_pos: QPoint) -> None:
    product = window.service.product_by_id(product_id)
    if product is None:
        return
    window._popup_product_id = product_id
    window.vision_popup.move(global_pos + QPoint(18, 18))
    if not product.image_path:
        window.vision_popup.show_error(product.name, "Attach a product screenshot first.")
        return
    if product.vision_cache.status == "ready" and product.vision_cache.image_hash:
        window.vision_popup.show_ready(product)
        return
    window.vision_popup.show_loading(product.name)
    start_vision_thread(window, product_id)
    window._rebuild_matrix()


def clear_popup_product(window) -> None:
    window._popup_product_id = None


def cleanup_vision_thread(window, product_id: str) -> None:
    thread_worker = window._vision_threads.pop(product_id, None)
    if thread_worker:
        thread, worker = thread_worker
        worker.deleteLater()
        thread.deleteLater()
    window._rebuild_matrix()


def on_vision_finished(window, product_id: str, _cache) -> None:
    window._refresh_all()
    if window._popup_product_id == product_id:
        product = window.service.product_by_id(product_id)
        if product:
            window.vision_popup.show_ready(product)


def on_vision_failed(window, product_id: str, message: str) -> None:
    window._refresh_all()
    product = window.service.product_by_id(product_id)
    if window._popup_product_id == product_id and product:
        window.vision_popup.show_error(product.name, message)


def review_popup_product(window, app_title: str) -> None:
    if window._popup_product_id is None:
        return
    product = window.service.product_by_id(window._popup_product_id)
    if product is None:
        return
    dialog = ProposalReviewDialog(product.vision_cache.proposals, window)
    if dialog.exec() != dialog.Accepted:
        return
    proposals = dialog.approved_proposals()
    applied = window.service.apply_vision_proposals(product.id, proposals)
    window._refresh_all()
    QMessageBox.information(window, app_title, "\n".join(applied) if applied else "No proposal was applied.")
