from __future__ import annotations

from html import escape
from pathlib import Path
from weakref import WeakValueDictionary

from .support import resolve_manual_path
from .theme import build_shell_stylesheet, get_shell_metrics, get_shell_palette, qt_t

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt shell runtime.") from exc


_MANUAL_DIALOG_CACHE: WeakValueDictionary[str, "ManualDialog"] = WeakValueDictionary()


def _manual_fallback_html(text: str) -> str:
    lines = text.splitlines()
    parts: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            parts.append(f"<p>{escape(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    def flush_code() -> None:
        nonlocal in_code, code_lines
        if in_code:
            parts.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
            in_code = False
            code_lines = []

    for line in lines:
        stripped = line.rstrip()
        bare = stripped.strip()
        if bare.startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code:
                flush_code()
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(stripped)
            continue
        if not bare:
            flush_paragraph()
            flush_list()
            continue
        if bare.startswith("#"):
            flush_paragraph()
            flush_list()
            level = min(6, len(bare) - len(bare.lstrip("#")))
            parts.append(f"<h{level}>{escape(bare[level:].strip())}</h{level}>")
            continue
        if bare.startswith(("- ", "* ")):
            flush_paragraph()
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{escape(bare[2:].strip())}</li>")
            continue
        paragraph.append(bare)

    flush_paragraph()
    flush_list()
    flush_code()
    return "".join(parts) or f"<p>{escape(text)}</p>"


def _load_manual_html(manual_path: Path) -> str:
    try:
        return manual_path.read_text(encoding="utf-8")
    except Exception:
        return f"<p>{escape(str(manual_path))}</p>"


class ManualDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, manual_path: Path):
        super().__init__(parent)
        self.manual_path = Path(manual_path)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setObjectName("manualDialog")
        self.resize(get_shell_metrics().manual_dialog_width, get_shell_metrics().manual_dialog_height)

        m = get_shell_metrics()
        p = get_shell_palette()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.manual_body_padding, m.manual_body_padding, m.manual_body_padding, m.manual_body_padding)
        layout.setSpacing(m.manual_section_spacing)

        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(m.manual_header_padding, m.manual_header_padding, m.manual_header_padding, m.manual_header_padding)
        header_layout.setSpacing(6)

        eyebrow = QLabel("Manual")
        eyebrow.setObjectName("eyebrow")
        header_layout.addWidget(eyebrow)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        header_layout.addWidget(title_label)

        meta = QLabel(self.manual_path.name)
        meta.setObjectName("summaryText")
        header_layout.addWidget(meta)
        layout.addWidget(header_card)

        viewer_card = QFrame()
        viewer_card.setObjectName("card")
        viewer_layout = QVBoxLayout(viewer_card)
        viewer_layout.setContentsMargins(8, 8, 8, 8)
        viewer_layout.setSpacing(0)

        viewer = QTextBrowser()
        viewer.setObjectName("manualViewer")
        viewer.setOpenExternalLinks(True)
        viewer.setFrameShape(QFrame.NoFrame)
        viewer.setReadOnly(True)
        viewer.document().setDocumentMargin(m.manual_body_padding - 4)
        viewer.document().setDefaultStyleSheet(
            f"""
            body {{ color: {p.text}; font-size: 13px; line-height: 1.55; }}
            h1, h2, h3, h4 {{ color: {p.text}; font-weight: 700; margin-top: 16px; margin-bottom: 8px; }}
            h1 {{ font-size: 24px; }}
            h2 {{ font-size: 19px; }}
            h3 {{ font-size: 16px; }}
            p {{ margin: 0 0 10px 0; }}
            ul, ol {{ margin: 0 0 12px 18px; }}
            li {{ margin-bottom: 6px; }}
            code {{ background: rgba(255,255,255,0.06); color: {p.accent_text}; padding: 2px 6px; border-radius: 6px; }}
            pre {{
                background: rgba(8, 10, 14, 0.55);
                border: 1px solid {p.control_border};
                border-radius: 12px;
                padding: 12px;
                margin: 10px 0 14px 0;
                color: {p.text};
                white-space: pre-wrap;
            }}
            blockquote {{
                margin: 10px 0;
                padding: 8px 12px;
                border-left: 3px solid {p.accent};
                background: rgba(61, 139, 255, 0.08);
                color: {p.text_muted};
            }}
            a {{ color: {p.accent_hover}; text-decoration: none; }}
            """
        )
        viewer.setStyleSheet(
            """
            QTextBrowser#manualViewer {
                background: transparent;
                border: none;
                selection-background-color: rgba(61, 139, 255, 0.26);
            }
            QTextBrowser#manualViewer QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 8px 0;
            }
            QTextBrowser#manualViewer QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.14);
                border-radius: 5px;
                min-height: 24px;
            }
            QTextBrowser#manualViewer QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.24);
            }
            QTextBrowser#manualViewer QScrollBar::add-line:vertical,
            QTextBrowser#manualViewer QScrollBar::sub-line:vertical,
            QTextBrowser#manualViewer QScrollBar::add-page:vertical,
            QTextBrowser#manualViewer QScrollBar::sub-page:vertical {
                background: transparent;
                height: 0px;
            }
            """
        )
        manual_body = _load_manual_html(self.manual_path)
        try:
            viewer.setMarkdown(manual_body)
        except Exception:
            viewer.setHtml(_manual_fallback_html(manual_body))
        self.viewer = viewer
        viewer_layout.addWidget(viewer)
        layout.addWidget(viewer_card, 1)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.setProperty("buttonRole", "pill")
        close_btn.clicked.connect(self.accept)
        action_row.addWidget(close_btn)
        layout.addLayout(action_row)


def open_manual_dialog(parent: QWidget | None, app_root: Path, title: str = "App Manual") -> ManualDialog | None:
    manual_path = resolve_manual_path(Path(app_root))
    if not manual_path:
        return None
    cache_key = str(manual_path)
    dialog = _MANUAL_DIALOG_CACHE.get(cache_key)
    if dialog is None:
        dialog = ManualDialog(parent, title, manual_path)
        dialog.setStyleSheet(build_shell_stylesheet())
        _MANUAL_DIALOG_CACHE[cache_key] = dialog
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog
