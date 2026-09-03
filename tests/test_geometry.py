import math

import pytest

from gesturecam.geometry import angle_degrees, distance, normalized_to_pixel


def test_distance_and_known_angle() -> None:
    assert distance((0.0, 0.0), (3.0, 4.0)) == 5.0
    assert angle_degrees((1.0, 0.0), (0.0, 0.0), (0.0, 1.0)) == pytest.approx(90.0)


def test_angle_zero_length_is_finite() -> None:
    result = angle_degrees((0.0, 0.0), (0.0, 0.0), (1.0, 1.0))
    assert result == 0.0
    assert math.isfinite(result)


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
