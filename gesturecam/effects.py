from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np

from .config import (
    BLUR_KERNEL_SIZE,
    CURSOR_RADIUS_PX,
    MIN_SELECTION_HEIGHT_PX,
    MIN_SELECTION_WIDTH_PX,
)
from .geometry import Point, Rect, cube_depth_px, normalized_to_pixel, rect_to_pixel_bounds
from .gestures import Gesture
from .interaction import InteractionController

HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (17, 0),
)


def apply_blur(frame: np.ndarray, rect: Rect | None) -> np.ndarray:
    if rect is None or frame.size == 0:
        return frame
    height, width = frame.shape[:2]
    left, top, right, bottom = rect_to_pixel_bounds(rect, width, height)
    if left >= right or top >= bottom:
        return frame
    roi = frame[top:bottom, left:right]
    if roi.size:
        frame[top:bottom, left:right] = cv2.GaussianBlur(
            roi,
            (BLUR_KERNEL_SIZE, BLUR_KERNEL_SIZE),
            0,
        )
    return frame


def apply_full_frame_blur(frame: np.ndarray) -> np.ndarray:
    if frame.size == 0:
        return frame
    frame[:] = cv2.GaussianBlur(
        frame,
        (BLUR_KERNEL_SIZE, BLUR_KERNEL_SIZE),
        0,
    )
    return frame


def draw_landmarks(frame: np.ndarray, landmarks: Sequence[Point]) -> None:
    height, width = frame.shape[:2]
    pixels = [normalized_to_pixel(point, width, height) for point in landmarks[:21]]
    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, pixels[start], pixels[end], (80, 220, 80), 2, cv2.LINE_AA)
    for point in pixels:
        cv2.circle(frame, point, 3, (40, 255, 255), -1, cv2.LINE_AA)


def draw_cursor(frame: np.ndarray, cursor: Point | None, pinching: bool) -> None:
    if cursor is None:
        return
    height, width = frame.shape[:2]
    color = (0, 180, 255) if pinching else (255, 220, 40)
    cv2.circle(frame, normalized_to_pixel(cursor, width, height), CURSOR_RADIUS_PX, color, 2, cv2.LINE_AA)


def draw_selection(frame: np.ndarray, rect: Rect | None) -> None:
    if rect is None:
        return
    height, width = frame.shape[:2]
    left, top, right, bottom = rect_to_pixel_bounds(rect, width, height)
    valid = right - left >= MIN_SELECTION_WIDTH_PX and bottom - top >= MIN_SELECTION_HEIGHT_PX
    color = (60, 220, 60) if valid else (40, 40, 230)
    cv2.rectangle(frame, (left, top), (max(left, right - 1), max(top, bottom - 1)), color, 2)
    label = "VALID" if valid else "TOO SMALL"
    cv2.putText(frame, label, (left, max(18, top - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


def draw_cube(frame: np.ndarray, rect: Rect | None) -> None:
    if rect is None:
        return
    height, width = frame.shape[:2]
    left, top, right, bottom = rect_to_pixel_bounds(rect, width, height)
    depth = min(cube_depth_px(rect, width, height), max(0, width - right), max(0, top))
    front_tl, front_br = (left, top), (max(left, right - 1), max(top, bottom - 1))
    back_tl = (left + depth, top - depth)
    back_br = (max(left + depth, right - 1 + depth), max(top - depth, bottom - 1 - depth))
    cv2.rectangle(frame, back_tl, back_br, (180, 180, 180), 2, cv2.LINE_AA)
    cv2.rectangle(frame, front_tl, front_br, (50, 240, 80), 3, cv2.LINE_AA)
    for front, back in zip(
        (front_tl, (front_br[0], front_tl[1]), front_br, (front_tl[0], front_br[1])),
        (back_tl, (back_br[0], back_tl[1]), back_br, (back_tl[0], back_br[1])),
    ):
        cv2.line(frame, front, back, (220, 200, 80), 2, cv2.LINE_AA)


def draw_status(
    frame: np.ndarray,
    controller: InteractionController,
    gesture: Gesture,
    hand_present: bool,
    fps: float,
    camera_index: int,
) -> None:
    lines = (
        f"Camera: {camera_index}",
        f"Mode: {controller.mode.name}",
        f"Gesture: {gesture.name}",
        f"State: {controller.state.name}",
        f"Hand: {'DETECTED' if hand_present else 'NOT DETECTED'}",
        f"FPS: {round(fps)}",
        "Keys: [B] Blur  [C] Cube  [Esc/Q] Exit",
    )
    panel_width = min(frame.shape[1], 440)
    cv2.rectangle(frame, (0, 0), (panel_width - 1, 205), (25, 25, 25), -1)
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
