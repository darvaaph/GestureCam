from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Sequence

from .config import (
    CURSOR_EMA_ALPHA,
    FLOAT_COMPARISON_TOLERANCE,
    FINGER_EXTENDED_ANGLE,
    FINGER_EXTENDED_RADIAL_RATIO,
    FINGER_FOLDED_ANGLE,
    FINGER_FOLDED_RADIAL_RATIO,
    PALM_SCALE_EPSILON,
    PINCH_ENTER_RATIO,
    PINCH_RELEASE_RATIO,
    STABLE_OBSERVATIONS,
    THUMB_EXTENDED_ANGLE,
    THUMB_EXTENDED_DISTANCE_RATIO,
    THUMB_FOLDED_DISTANCE_RATIO,
)
from .geometry import Point, angle_degrees, distance, valid_landmarks

WRIST = 0
THUMB_MCP, THUMB_IP, THUMB_TIP = 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_MCP, RING_PIP, RING_TIP = 13, 14, 16
PINKY_MCP, PINKY_PIP, PINKY_TIP = 17, 18, 20
FINGER_JOINTS = (
    (INDEX_MCP, INDEX_PIP, INDEX_TIP),
    (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP),
    (RING_MCP, RING_PIP, RING_TIP),
    (PINKY_MCP, PINKY_PIP, PINKY_TIP),
)


class Gesture(Enum):
    OPEN_PALM = auto()
    FIST = auto()
    POINTING = auto()
    PINCH = auto()
    UNKNOWN = auto()


class FingerPosture(Enum):
    EXTENDED = auto()
    FOLDED = auto()
    AMBIGUOUS = auto()


@dataclass(frozen=True)
class GestureUpdate:
    stable_gesture: Gesture
    entered: Gesture | None = None
    held: bool = False
    released: Gesture | None = None


def _finger_posture(landmarks: Sequence[Point], joints: tuple[int, int, int]) -> FingerPosture:
    mcp, pip, tip = (landmarks[index] for index in joints)
    angle = angle_degrees(mcp, pip, tip)
    tip_radius = distance(tip, landmarks[WRIST])
    pip_radius = distance(pip, landmarks[WRIST])
    if angle >= FINGER_EXTENDED_ANGLE and tip_radius >= FINGER_EXTENDED_RADIAL_RATIO * pip_radius:
        return FingerPosture.EXTENDED
    if angle <= FINGER_FOLDED_ANGLE or tip_radius <= FINGER_FOLDED_RADIAL_RATIO * pip_radius:
        return FingerPosture.FOLDED
    return FingerPosture.AMBIGUOUS


def _thumb_posture(landmarks: Sequence[Point], palm_scale: float) -> FingerPosture:
    angle = angle_degrees(landmarks[THUMB_MCP], landmarks[THUMB_IP], landmarks[THUMB_TIP])
    separation_ratio = distance(landmarks[THUMB_TIP], landmarks[INDEX_MCP]) / palm_scale
    if angle >= THUMB_EXTENDED_ANGLE and separation_ratio >= THUMB_EXTENDED_DISTANCE_RATIO:
        return FingerPosture.EXTENDED
    if separation_ratio <= THUMB_FOLDED_DISTANCE_RATIO:
        return FingerPosture.FOLDED
    return FingerPosture.AMBIGUOUS


class RawGestureRecognizer:
    def __init__(self) -> None:
        self.pinch_active = False
        self.pinch_ratio: float | None = None
        self.pinch_release_observation = False

    def classify(self, landmarks: Sequence[Point] | None) -> Gesture:
        self.pinch_release_observation = False
        if not valid_landmarks(landmarks):
            self.pinch_ratio = None
            return Gesture.UNKNOWN
        assert landmarks is not None
        palm_scale = max(distance(landmarks[WRIST], landmarks[MIDDLE_MCP]), PALM_SCALE_EPSILON)
        self.pinch_ratio = distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / palm_scale
        self._update_pinch(self.pinch_ratio)
        if self.pinch_active:
            return Gesture.PINCH

        fingers = tuple(_finger_posture(landmarks, joints) for joints in FINGER_JOINTS)
        thumb = _thumb_posture(landmarks, palm_scale)
        if (
            all(posture is FingerPosture.FOLDED for posture in fingers)
            and thumb is not FingerPosture.EXTENDED
        ):
            return Gesture.FIST
        if fingers[0] is FingerPosture.EXTENDED and all(
            posture is FingerPosture.FOLDED for posture in fingers[1:]
        ):
            return Gesture.POINTING
        if all(posture is FingerPosture.EXTENDED for posture in fingers) and thumb is FingerPosture.EXTENDED:
            return Gesture.OPEN_PALM
        return Gesture.UNKNOWN

    def _update_pinch(self, ratio: float) -> None:
        if self.pinch_active and ratio >= PINCH_RELEASE_RATIO - FLOAT_COMPARISON_TOLERANCE:
            self.pinch_active = False
        elif not self.pinch_active and ratio <= PINCH_ENTER_RATIO + FLOAT_COMPARISON_TOLERANCE:
            self.pinch_active = True
        self.pinch_release_observation = (
            not self.pinch_active
            and ratio >= PINCH_RELEASE_RATIO - FLOAT_COMPARISON_TOLERANCE
        )


class GestureStabilizer:
    def __init__(self) -> None:
        self.stable_gesture = Gesture.UNKNOWN
        self._candidate = Gesture.UNKNOWN
        self._candidate_count = 0
        self._pinch_release_count = 0
        self._stable_confirmed = False

    def update(self, raw_gesture: Gesture, pinch_release_observation: bool = False) -> GestureUpdate:
        if raw_gesture is self._candidate:
            self._candidate_count += 1
        else:
            self._candidate = raw_gesture
            self._candidate_count = 1

        if self.stable_gesture is Gesture.PINCH:
            return self._update_stable_pinch(raw_gesture, pinch_release_observation)

        entered = released = None
        stable_changed = raw_gesture is not self.stable_gesture
        if self._candidate_count >= STABLE_OBSERVATIONS and (stable_changed or not self._stable_confirmed):
            released = (
                self.stable_gesture
                if self._stable_confirmed and self.stable_gesture is not Gesture.UNKNOWN
                else None
            )
            self.stable_gesture = raw_gesture
            self._stable_confirmed = True
            entered = raw_gesture
        held = (
            self._stable_confirmed
            and entered is None
            and raw_gesture is self.stable_gesture
            and raw_gesture is not Gesture.UNKNOWN
        )
        return GestureUpdate(self.stable_gesture, entered, held, released)

    def _update_stable_pinch(self, raw_gesture: Gesture, release_observation: bool) -> GestureUpdate:
        if raw_gesture is Gesture.PINCH:
            self._pinch_release_count = 0
            return GestureUpdate(Gesture.PINCH, held=True)
        self._pinch_release_count = self._pinch_release_count + 1 if release_observation else 0
        if self._pinch_release_count < STABLE_OBSERVATIONS:
            return GestureUpdate(Gesture.PINCH)

        self._pinch_release_count = 0
        self.stable_gesture = Gesture.UNKNOWN
        self._stable_confirmed = True
        entered = None
        if self._candidate_count >= STABLE_OBSERVATIONS:
            self.stable_gesture = raw_gesture
            entered = raw_gesture
        return GestureUpdate(self.stable_gesture, entered=entered, released=Gesture.PINCH)


class CursorSmoother:
    def __init__(self, alpha: float = CURSOR_EMA_ALPHA) -> None:
        self.alpha = alpha
        self.value: Point | None = None

    def update(self, landmarks: Sequence[Point], pinch_active: bool) -> Point:
        index_tip = landmarks[INDEX_TIP]
        thumb_tip = landmarks[THUMB_TIP]
        target = (
            ((index_tip[0] + thumb_tip[0]) / 2.0, (index_tip[1] + thumb_tip[1]) / 2.0)
            if pinch_active
            else index_tip
        )
        if self.value is None:
            self.value = target
        else:
            self.value = (
                self.alpha * target[0] + (1.0 - self.alpha) * self.value[0],
                self.alpha * target[1] + (1.0 - self.alpha) * self.value[1],
            )
        return self.value

    def reset(self) -> None:
        self.value = None
