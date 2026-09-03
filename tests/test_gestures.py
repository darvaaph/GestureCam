import pytest

from gesturecam.gestures import (
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
    return points


def pointing_hand():
    points = open_hand()
    for indices in ((9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)):
        fold_finger(points, indices)
    return points


def peace_hand():
    points = open_hand()
    for indices in ((13, 14, 15, 16), (17, 18, 19, 20)):
        fold_finger(points, indices)
    return points


def three_fingers_hand():
    points = peace_hand()
    points[13:17] = open_hand()[13:17]
    return points


def test_peace_gesture_detected() -> None:
    assert RawGestureRecognizer().classify(peace_hand()) is Gesture.PEACE


@pytest.mark.parametrize(
    "hand_fn",
    [open_hand, fist_hand, pointing_hand, three_fingers_hand],
)
def test_non_peace_gestures_are_unknown(hand_fn) -> None:
    assert RawGestureRecognizer().classify(hand_fn()) is Gesture.UNKNOWN


def test_peace_ignores_thumb_position() -> None:
    hand = peace_hand()
    # Vary thumb coordinates drastically
    hand[4] = hand[5]
    assert RawGestureRecognizer().classify(hand) is Gesture.PEACE
    hand[4] = (0.1, 0.9)
    assert RawGestureRecognizer().classify(hand) is Gesture.PEACE


def test_ambiguous_pose_is_unknown() -> None:
    points = open_hand()
    points[2], points[3], points[4] = (0.50, 0.55), (0.40, 0.55), (0.30, 0.55)
    assert RawGestureRecognizer().classify(points) is Gesture.UNKNOWN


def test_scale_equivalent_hands_match() -> None:
    original = peace_hand()
    scaled = [(0.2 + x * 0.5, 0.1 + y * 0.5) for x, y in original]
    assert RawGestureRecognizer().classify(original) is RawGestureRecognizer().classify(scaled)


@pytest.mark.parametrize("landmarks", [None, [(0.0, 0.0)] * 20, [(float("nan"), 0.0)] * 21])
def test_invalid_landmarks_return_unknown(landmarks) -> None:
    assert RawGestureRecognizer().classify(landmarks) is Gesture.UNKNOWN


def test_one_noisy_frame_does_not_change_stable_gesture() -> None:
    stabilizer = GestureStabilizer()
    for _ in range(3):
        stabilizer.update(Gesture.UNKNOWN)
    result = stabilizer.update(Gesture.PEACE)
    assert result.stable_gesture is Gesture.UNKNOWN


def test_three_consecutive_frames_activate_peace() -> None:
    stabilizer = GestureStabilizer()
    assert stabilizer.update(Gesture.PEACE).stable_gesture is Gesture.UNKNOWN
    assert stabilizer.update(Gesture.PEACE).stable_gesture is Gesture.UNKNOWN
    assert stabilizer.update(Gesture.PEACE).stable_gesture is Gesture.PEACE
    # Stays stable on subsequent frames
    assert stabilizer.update(Gesture.PEACE).stable_gesture is Gesture.PEACE


def test_dropping_peace_returns_to_unknown_after_debounce() -> None:
    stabilizer = GestureStabilizer()
    for _ in range(3):
        stabilizer.update(Gesture.PEACE)
    assert stabilizer.stable_gesture is Gesture.PEACE

    # Drop peace
    assert stabilizer.update(Gesture.UNKNOWN).stable_gesture is Gesture.PEACE
    assert stabilizer.update(Gesture.UNKNOWN).stable_gesture is Gesture.PEACE
    assert stabilizer.update(Gesture.UNKNOWN).stable_gesture is Gesture.UNKNOWN
