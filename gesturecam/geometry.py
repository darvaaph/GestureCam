from __future__ import annotations

from math import acos, degrees, hypot, isfinite
from typing import Sequence

Point = tuple[float, float]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def distance(a: Point, b: Point) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


def angle_degrees(a: Point, vertex: Point, c: Point) -> float:
    first = (a[0] - vertex[0], a[1] - vertex[1])
    second = (c[0] - vertex[0], c[1] - vertex[1])
    denominator = hypot(*first) * hypot(*second)
    if denominator == 0.0:
        return 0.0
    cosine = clamp((first[0] * second[0] + first[1] * second[1]) / denominator, -1.0, 1.0)
    return degrees(acos(cosine))


def valid_point(point: Point) -> bool:
    return len(point) == 2 and isfinite(point[0]) and isfinite(point[1])


def valid_landmarks(landmarks: Sequence[Point] | None) -> bool:
    return landmarks is not None and len(landmarks) >= 21 and all(valid_point(p) for p in landmarks[:21])


def normalized_to_pixel(point: Point, frame_width: int, frame_height: int) -> tuple[int, int]:
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame dimensions must be positive")
    x = round(clamp(point[0], 0.0, 1.0) * (frame_width - 1))
    y = round(clamp(point[1], 0.0, 1.0) * (frame_height - 1))
    return int(x), int(y)
