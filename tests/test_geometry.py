import math

import pytest

from gesturecam.geometry import (
    Rect,
    angle_degrees,
    clamp_cube_rect,
    distance,
    normalized_to_pixel,
    rect_to_pixel_bounds,
)


def test_distance_and_known_angle() -> None:
    assert distance((0.0, 0.0), (3.0, 4.0)) == 5.0
    assert angle_degrees((1.0, 0.0), (0.0, 0.0), (0.0, 1.0)) == pytest.approx(90.0)


def test_angle_zero_length_is_finite() -> None:
    result = angle_degrees((0.0, 0.0), (0.0, 0.0), (1.0, 1.0))
    assert result == 0.0
    assert math.isfinite(result)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ((0.2, 0.3), (0.8, 0.9)),
        ((0.8, 0.3), (0.2, 0.9)),
        ((0.2, 0.9), (0.8, 0.3)),
        ((0.8, 0.9), (0.2, 0.3)),
    ],
)
def test_rectangle_normalizes_all_drag_directions(first, second) -> None:
    assert Rect.from_points(first, second) == Rect(0.2, 0.3, 0.8, 0.9)


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        ((-0.2, -1.0), (0, 0)),
        ((1.0, 1.0), (99, 49)),
        ((1.4, 2.0), (99, 49)),
    ],
)
def test_normalized_to_pixel_clamps(point, expected) -> None:
    assert normalized_to_pixel(point, 100, 50) == expected


def test_roi_bounds_use_exclusive_right_and_bottom() -> None:
    assert rect_to_pixel_bounds(Rect(0.0, 0.0, 1.0, 1.0), 100, 50) == (0, 0, 100, 50)


def test_rectangle_hit_testing_includes_boundaries() -> None:
    rect = Rect(0.2, 0.3, 0.8, 0.9)
    assert rect.contains((0.2, 0.3))
    assert rect.contains((0.8, 0.9))
    assert not rect.contains((0.19, 0.3))


def test_cube_translation_is_clamped_with_back_face_visible() -> None:
    rect = Rect(0.2, 0.3, 0.5, 0.6)
    moved = clamp_cube_rect(rect, 0.95, -0.4, 100, 100)
    assert moved.top >= 0.12
    assert moved.right == pytest.approx(0.88)
    assert moved.width == pytest.approx(rect.width)
    assert moved.height == pytest.approx(rect.height)
