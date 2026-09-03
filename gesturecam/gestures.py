from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Sequence

from .config import (
    FINGER_EXTENDED_ANGLE,
    FINGER_EXTENDED_RADIAL_RATIO,
    FINGER_FOLDED_ANGLE,
    FINGER_FOLDED_RADIAL_RATIO,
    STABLE_OBSERVATIONS,
)
from .geometry import Point, angle_degrees, distance, valid_landmarks

WRIST = 0
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
    PEACE = auto()
    UNKNOWN = auto()


class FingerPosture(Enum):
    EXTENDED = auto()
    FOLDED = auto()
    AMBIGUOUS = auto()


@dataclass(frozen=True)
class GestureUpdate:
    stable_gesture: Gesture


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


class RawGestureRecognizer:
    def classify(self, landmarks: Sequence[Point] | None) -> Gesture:
        if not valid_landmarks(landmarks):
            return Gesture.UNKNOWN
        assert landmarks is not None

        fingers = tuple(_finger_posture(landmarks, joints) for joints in FINGER_JOINTS)
        if (
            fingers[0] is FingerPosture.EXTENDED
            and fingers[1] is FingerPosture.EXTENDED
            and fingers[2] is FingerPosture.FOLDED
            and fingers[3] is FingerPosture.FOLDED
        ):
            return Gesture.PEACE
        return Gesture.UNKNOWN


class GestureStabilizer:
    def __init__(self) -> None:
        self.stable_gesture = Gesture.UNKNOWN
        self._candidate = Gesture.UNKNOWN
        self._candidate_count = 0

    def update(self, raw_gesture: Gesture) -> GestureUpdate:
        if raw_gesture is self._candidate:
            self._candidate_count += 1
        else:
            self._candidate = raw_gesture
            self._candidate_count = 1

        if self._candidate_count >= STABLE_OBSERVATIONS:
            self.stable_gesture = self._candidate

        return GestureUpdate(self.stable_gesture)
