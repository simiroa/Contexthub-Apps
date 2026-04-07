from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShellMetrics:
    window_radius: int = 18
    card_radius: int = 16
    panel_radius: int = 14
    shell_margin: int = 18
    card_padding: int = 16
    section_gap: int = 14
    panel_padding: int = 14
    field_radius: int = 8
    header_padding_x: int = 16
    header_padding_y_top: int = 12
    header_padding_y_bottom: int = 12
    header_row_gap: int = 10
    header_icon_size: int = 24
    header_badge_height: int = 42
    preview_min_height: int = 300
    primary_button_height: int = 26
    input_min_height: int = 26
    manual_dialog_width: int = 760
    manual_dialog_height: int = 780
    control_size: int = 42
    title_btn_size: int = 28
    title_btn_radius: int = 8
    input_padding_y: int = 4
    input_padding_x: int = 12
    button_padding_y: int = 4
    button_padding_x: int = 12
    group_title_offset_left: int = 14
    group_title_offset_top: int = 8
    asset_list_min_height: int = 260
    utility_button_size: int = 46
    summary_row_gap: int = 10
    collapsible_padding: int = 10
    collapsible_gap: int = 8
    collapsible_toggle_size: int = 28
    collapsible_body_gap: int = 10
    manual_body_padding: int = 22
    manual_header_padding: int = 18
    manual_section_spacing: int = 16


def get_shell_metrics() -> ShellMetrics:
    return ShellMetrics()
