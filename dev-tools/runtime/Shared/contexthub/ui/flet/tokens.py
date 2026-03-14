from __future__ import annotations


COLORS = {
    "app_bg": "#090B11",
    "surface": "#11161F",
    "surface_alt": "#0E1420",
    "surface_soft": "#0B1220",
    "surface_accent": "#0E1726",
    "field_bg": "#131B27",
    "line": "#253042",
    "line_strong": "#2D6AE3",
    "text": "#F3F6FF",
    "text_muted": "#9AA7B8",
    "text_soft": "#7B8797",
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "success": "#16A34A",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "info": "#334155",
}

RADII = {
    "sm": 12,
    "md": 16,
    "lg": 20,
    "xl": 24,
    "pill": 999,
}

SPACING = {
    "xs": 8,
    "sm": 12,
    "md": 16,
    "lg": 20,
    "xl": 24,
}

WINDOWS = {
    "desktop": {
        "width": 1280,
        "height": 900,
        "min_width": 1120,
        "min_height": 760,
    },
    "form": {
        "width": 860,
        "height": 860,
        "min_width": 760,
        "min_height": 760,
    },
    "two_pane": {
        "width": 1120,
        "height": 920,
        "min_width": 980,
        "min_height": 760,
    },
    "wide_canvas": {
        "width": 1280,
        "height": 860,
        "min_width": 1120,
        "min_height": 760,
    },
    "table_heavy": {
        "width": 1240,
        "height": 920,
        "min_width": 1080,
        "min_height": 780,
    },
    "compact": {
        "width": 640,
        "height": 520,
        "min_width": 560,
        "min_height": 420,
    },
    "wide": {
        "width": 1100,
        "height": 750,
        "min_width": 1000,
        "min_height": 720,
    },
    "dialog": {
        "width": 440,
    },
    "side_panel_width": 360,
}

CONTROL_WIDTHS = {
    "profile": 220,
    "tone": 150,
    "language": 160,
}

SIZES = {
    "avatar": 42,
    "avatar_radius": 21,
    "message_padding": 18,
    "profile_list_height": 220,
    "badge_horizontal": 10,
    "badge_vertical": 4,
    "mini_badge_horizontal": 8,
    "mini_badge_vertical": 3,
}

MODE_COLORS = {
    "custom_voice": "#3B82F6",
    "voice_clone": "#F59E0B",
    "voice_design": "#10B981",
}

STATUS_COLORS = {
    "ready": "#64748B",
    "queued": "#2563EB",
    "done": "#16A34A",
    "error": "#EF4444",
}


def mode_color(mode: str) -> str:
    return MODE_COLORS.get(mode or "", COLORS["accent"])


def status_color(status: str) -> str:
    return STATUS_COLORS.get((status or "").lower(), COLORS["info"])


def profile_color_seed(name: str) -> str:
    palette = [
        "#3B82F6",
        "#F59E0B",
        "#10B981",
        "#EC4899",
        "#8B5CF6",
        "#06B6D4",
    ]
    if not name:
        return palette[0]
    return palette[sum(ord(char) for char in name) % len(palette)]
