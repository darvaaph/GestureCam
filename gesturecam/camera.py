from __future__ import annotations

from collections.abc import Callable
from typing import Any

import cv2
import numpy as np

from .config import (
    MAX_CONSECUTIVE_READ_FAILURES,
    REQUEST_FPS,
    REQUEST_HEIGHT,
    REQUEST_WIDTH,
)


class Camera:
    def __init__(
        self,
        capture_factory: Callable[[int], Any] = cv2.VideoCapture,
        camera_index: int = 0,
    ) -> None:
        self._capture_factory = capture_factory
        self.camera_index = camera_index
        self._capture: Any | None = None
        self._consecutive_failures = 0

    def open(self) -> None:
        self._capture = self._capture_factory(self.camera_index)
        if not self._capture.isOpened():
            self.close()
            raise RuntimeError(
                f"Camera index {self.camera_index} could not be opened. "
                "Check Windows camera permission, try another --camera index, "
                "and close other applications using the webcam."
            )
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, REQUEST_WIDTH)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, REQUEST_HEIGHT)
        self._capture.set(cv2.CAP_PROP_FPS, REQUEST_FPS)

    def read(self) -> np.ndarray | None:
        if self._capture is None:
            raise RuntimeError("Camera is not open.")
        success, frame = self._capture.read()
        if success and frame is not None:
            self._consecutive_failures = 0
            return frame
        self._consecutive_failures += 1
        if self._consecutive_failures >= MAX_CONSECUTIVE_READ_FAILURES:
            raise RuntimeError(
                f"Camera index {self.camera_index} frame stream failed 30 consecutive times. "
                "Reconnect the camera or close other applications using it."
            )
        return None

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
