from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ViewportState:
    yaw_degrees: float = -35.0
    pitch_degrees: float = 24.0
    distance_scale: float = 2.5
    pan_x: float = 0.0
    pan_y: float = 0.0
    wireframe: bool = False


def reset_view(state: ViewportState) -> None:
    state.yaw_degrees = -35.0
    state.pitch_degrees = 24.0
    state.distance_scale = 2.5
    state.pan_x = 0.0
    state.pan_y = 0.0


def fit_view(state: ViewportState) -> None:
    state.distance_scale = 2.1
    state.pan_x = 0.0
    state.pan_y = 0.0
