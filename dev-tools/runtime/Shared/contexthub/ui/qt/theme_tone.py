from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor

from .theme_palette import ShellPalette, get_shell_palette


@dataclass(frozen=True)
class ToneSpec:
    base: str
    fill: str
    border: str
    text: str


def _rgba(hex_color: str, alpha: int) -> str:
    color = QColor(hex_color)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


def _lift_color(hex_color: str, factor: int) -> str:
    return QColor(hex_color).lighter(factor).name()


def get_shell_accent_cycle(palette: ShellPalette | None = None) -> list[str]:
    p = palette or get_shell_palette()
    return [
        p.text_muted,
        p.success,
        p.warning,
        p.accent,
        p.error,
        _lift_color(p.accent, 130),
        _lift_color(p.warning, 125),
        _lift_color(p.success, 120),
    ]


def get_tone_spec(tone: str = "default", palette: ShellPalette | None = None) -> ToneSpec:
    p = palette or get_shell_palette()
    base_map = {
        "default": p.accent,
        "accent": p.accent,
        "success": p.success,
        "warning": p.warning,
        "error": p.error,
        "muted": p.text_muted,
    }
    text_map = {
        "default": p.text,
        "accent": p.chip_text,
        "success": p.text,
        "warning": p.text,
        "error": p.text,
        "muted": p.text_muted,
    }
    base = base_map.get(tone, p.accent)
    return ToneSpec(
        base=base,
        fill=_rgba(base, 34 if tone in {"default", "muted"} else 42),
        border=_rgba(base, 82 if tone in {"default", "muted"} else 118),
        text=text_map.get(tone, p.text),
    )
