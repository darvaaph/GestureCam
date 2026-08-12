from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, hypot, isfinite
from typing import Sequence

from .config import (
    CUBE_DEPTH_MAX_PX,
    CUBE_DEPTH_MIN_PX,
    CUBE_DEPTH_RATIO,
)

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


@dataclass(frozen=True)
class Rect:
    left: float
    top: float
    right: float
    bottom: float

    @classmethod
    def from_points(cls, first: Point, second: Point) -> "Rect":
        return cls(
            min(first[0], second[0]),
            min(first[1], second[1]),
            max(first[0], second[0]),
            max(first[1], second[1]),
        )

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def contains(self, point: Point) -> bool:
        return self.left <= point[0] <= self.right and self.top <= point[1] <= self.bottom

    def translated(self, left: float, top: float) -> "Rect":
        return Rect(left, top, left + self.width, top + self.height)


def normalized_to_pixel(point: Point, frame_width: int, frame_height: int) -> tuple[int, int]:
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame dimensions must be positive")
    x = round(clamp(point[0], 0.0, 1.0) * (frame_width - 1))
    y = round(clamp(point[1], 0.0, 1.0) * (frame_height - 1))
    return int(x), int(y)


def rect_to_pixel_bounds(rect: Rect, frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
    normalized = Rect.from_points((rect.left, rect.top), (rect.right, rect.bottom))
    left = int(round(clamp(normalized.left, 0.0, 1.0) * frame_width))
    top = int(round(clamp(normalized.top, 0.0, 1.0) * frame_height))
    right = int(round(clamp(normalized.right, 0.0, 1.0) * frame_width))
    bottom = int(round(clamp(normalized.bottom, 0.0, 1.0) * frame_height))
    return left, top, right, bottom


def cube_depth_px(rect: Rect, frame_width: int, frame_height: int) -> int:
    left, top, right, bottom = rect_to_pixel_bounds(rect, frame_width, frame_height)
    raw_depth = round(CUBE_DEPTH_RATIO * min(right - left, bottom - top))
    return int(clamp(raw_depth, CUBE_DEPTH_MIN_PX, CUBE_DEPTH_MAX_PX))


def clamp_cube_rect(rect: Rect, desired_left: float, desired_top: float, frame_width: int, frame_height: int) -> Rect:
    depth = cube_depth_px(rect, frame_width, frame_height)
    min_left = 0.0
    min_top = depth / frame_height
    max_left = max(min_left, 1.0 - depth / frame_width - rect.width)
    max_top = max(min_top, 1.0 - rect.height)
    return rect.translated(
        clamp(desired_left, min_left, max_left),
        clamp(desired_top, min_top, max_top),
    )
