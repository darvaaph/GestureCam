from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np

from .config import BLUR_KERNEL_SIZE
from .geometry import Point, normalized_to_pixel
from .gestures import Gesture

HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (17, 0),
)


def apply_full_frame_blur(frame: np.ndarray) -> np.ndarray:
    if frame.size == 0:
        return frame
    frame[:] = cv2.GaussianBlur(frame, (BLUR_KERNEL_SIZE, BLUR_KERNEL_SIZE), 0)
    return frame


def draw_landmarks(frame: np.ndarray, landmarks: Sequence[Point]) -> None:
    height, width = frame.shape[:2]
    pixels = [normalized_to_pixel(point, width, height) for point in landmarks[:21]]
    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, pixels[start], pixels[end], (80, 220, 80), 2, cv2.LINE_AA)
    for point in pixels:
        cv2.circle(frame, point, 3, (40, 255, 255), -1, cv2.LINE_AA)


def draw_status(
    frame: np.ndarray,
    gestures: Sequence[Gesture],
    hand_count: int,
    fps: float,
    camera_index: int,
) -> None:
    gesture_text = " | ".join(item.name for item in gestures) if gestures else Gesture.UNKNOWN.name
    blur_active = Gesture.PEACE in gestures
    lines = (
        f"Camera: {camera_index}",
        f"Gestures: {gesture_text}",
        f"Hands: {hand_count}/2",
        f"Blur: {'ACTIVE' if blur_active else 'OFF'}",
        f"FPS: {round(fps)}",
        "Show a peace sign to blur  |  [Esc/Q] Exit",
    )
    panel_width = min(frame.shape[1], 500)
    cv2.rectangle(frame, (0, 0), (panel_width - 1, 178), (25, 25, 25), -1)
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (12, 25 + index * 27),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            (245, 245, 245),
            1,
            cv2.LINE_AA,
        )
