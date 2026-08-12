from copy import deepcopy

import pytest

from gesturecam.gestures import (
    CursorSmoother,
    Gesture,
    GestureStabilizer,
    RawGestureRecognizer,
)


def open_hand():
    points = [(0.5, 0.8)] * 21
    points[0] = (0.5, 0.8)
    points[1:5] = [(0.43, 0.68), (0.36, 0.62), (0.24, 0.55), (0.12, 0.48)]
    points[5:9] = [(0.42, 0.55), (0.42, 0.38), (0.42, 0.24), (0.42, 0.10)]
    points[9:13] = [(0.50, 0.50), (0.50, 0.32), (0.50, 0.18), (0.50, 0.05)]
    points[13:17] = [(0.58, 0.55), (0.58, 0.38), (0.58, 0.25), (0.58, 0.12)]
    points[17:21] = [(0.66, 0.60), (0.66, 0.44), (0.66, 0.32), (0.66, 0.20)]
    return points


def fold_finger(points, indices):
    mcp, pip, dip, tip = indices
    base = points[mcp]
    points[pip] = (base[0], base[1] - 0.10)
    points[dip] = (base[0] + 0.03, base[1] - 0.04)
    points[tip] = (base[0] + 0.05, base[1] + 0.01)


def fist_hand():
    points = open_hand()
    for indices in ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)):
        fold_finger(points, indices)
    points[4] = (0.32, 0.65)
    return points


def pointing_hand():
    points = open_hand()
    for indices in ((9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)):
        fold_finger(points, indices)
    return points


def pinch_hand(ratio=0.1):
    points = open_hand()
    palm_scale = 0.3
    points[4] = (points[8][0] + ratio * palm_scale, points[8][1])
    return points


@pytest.mark.parametrize(
    ("builder", "expected"),
    [
        (open_hand, Gesture.OPEN_PALM),
        (fist_hand, Gesture.FIST),
        (pointing_hand, Gesture.POINTING),
        (pinch_hand, Gesture.PINCH),
    ],
)
def test_canonical_gestures(builder, expected) -> None:
    assert RawGestureRecognizer().classify(builder()) is expected


def test_ambiguous_pose_is_unknown() -> None:
    points = open_hand()
    points[2], points[3], points[4] = (0.50, 0.55), (0.40, 0.55), (0.30, 0.55)
    assert RawGestureRecognizer().classify(points) is Gesture.UNKNOWN


def test_pinch_thresholds_and_hysteresis() -> None:
    recognizer = RawGestureRecognizer()
    assert recognizer.classify(pinch_hand(0.35)) is Gesture.PINCH
    assert recognizer.classify(pinch_hand(0.42)) is Gesture.PINCH
    assert recognizer.classify(pinch_hand(0.50)) is not Gesture.PINCH
    assert recognizer.pinch_release_observation


def test_pinch_has_priority_over_finger_postures() -> None:
    points = fist_hand()
    points[4] = (points[8][0] + 0.01, points[8][1])
    assert RawGestureRecognizer().classify(points) is Gesture.PINCH


def test_fist_rejects_extended_thumb_but_pointing_ignores_thumb() -> None:
    fist = fist_hand()
    fist[2:5] = open_hand()[2:5]
    pointing = pointing_hand()
    pointing[4] = pointing[5]
    assert RawGestureRecognizer().classify(fist) is Gesture.UNKNOWN
    assert RawGestureRecognizer().classify(pointing) is Gesture.POINTING


def test_scale_equivalent_hands_match() -> None:
    original = open_hand()
    scaled = [(0.2 + x * 0.5, 0.1 + y * 0.5) for x, y in original]
    assert RawGestureRecognizer().classify(original) is RawGestureRecognizer().classify(scaled)


@pytest.mark.parametrize("landmarks", [None, [(0.0, 0.0)] * 20, [(float("nan"), 0.0)] * 21])
def test_invalid_landmarks_return_unknown(landmarks) -> None:
    assert RawGestureRecognizer().classify(landmarks) is Gesture.UNKNOWN


def test_one_noisy_frame_does_not_change_stable_gesture() -> None:
    stabilizer = GestureStabilizer()
    for _ in range(3):
        stabilizer.update(Gesture.OPEN_PALM)
    result = stabilizer.update(Gesture.FIST)
    assert result.stable_gesture is Gesture.OPEN_PALM
    assert result.entered is None


def test_three_observations_emit_one_enter_and_hold_does_not_repeat() -> None:
    stabilizer = GestureStabilizer()
    results = [stabilizer.update(Gesture.POINTING) for _ in range(4)]
    assert [result.entered for result in results] == [None, None, Gesture.POINTING, None]
    assert results[-1].held


def test_unknown_becomes_stable_after_three_observations_without_action() -> None:
    stabilizer = GestureStabilizer()
    results = [stabilizer.update(Gesture.UNKNOWN) for _ in range(4)]
    assert [result.entered for result in results] == [None, None, Gesture.UNKNOWN, None]
    assert not any(result.held for result in results)


def test_three_release_observations_emit_one_pinch_release() -> None:
    stabilizer = GestureStabilizer()
    for _ in range(3):
        stabilizer.update(Gesture.PINCH)
    results = [stabilizer.update(Gesture.POINTING, True) for _ in range(4)]
    assert [result.released for result in results] == [None, None, Gesture.PINCH, None]
    assert results[2].entered is Gesture.POINTING


def test_cursor_ema_initializes_at_target_and_resets() -> None:
    points = open_hand()
    smoother = CursorSmoother(alpha=0.35)
    assert smoother.update(points, False) == points[8]
    moved = deepcopy(points)
    moved[8] = (0.82, 0.50)
    assert smoother.update(moved, False) == pytest.approx((0.56, 0.24))
    smoother.reset()
    assert smoother.update(moved, False) == moved[8]
