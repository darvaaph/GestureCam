from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from .geometry import Point


class HandTracker:
    def __init__(self, model_path: Path) -> None:
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.60,
            min_hand_presence_confidence=0.60,
            min_tracking_confidence=0.60,
        )
        try:
            self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        except (RuntimeError, ValueError) as exc:
            raise RuntimeError(
                f"MediaPipe Hand Landmarker could not initialize from {model_path}. "
                "Re-download the model and verify the pinned dependencies."
            ) from exc
        self._last_timestamp_ms = -1

    def detect(self, mirrored_bgr_frame: np.ndarray, timestamp_ms: int) -> list[list[Point]]:
        timestamp_ms = max(timestamp_ms, self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms
        rgb = cv2.cvtColor(mirrored_bgr_frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        return [
            [(float(item.x), float(item.y)) for item in hand]
            for hand in result.hand_landmarks[:2]
        ]

    def close(self) -> None:
        self._landmarker.close()
