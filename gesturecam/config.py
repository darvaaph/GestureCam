from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_PYTHON = (3, 12)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "assets" / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)

REQUEST_WIDTH = 1280
REQUEST_HEIGHT = 720
REQUEST_FPS = 30
MAX_CONSECUTIVE_READ_FAILURES = 30
WINDOW_NAME = "GestureCam"

HAND_LOSS_GRACE_MS = 250
MIN_SELECTION_WIDTH_PX = 30
MIN_SELECTION_HEIGHT_PX = 30
CURSOR_RADIUS_PX = 8
CUBE_DEPTH_MIN_PX = 12
CUBE_DEPTH_MAX_PX = 40
CUBE_DEPTH_RATIO = 0.15
BLUR_KERNEL_SIZE = 31

PALM_SCALE_EPSILON = 1e-6
FLOAT_COMPARISON_TOLERANCE = 1e-9
FINGER_EXTENDED_ANGLE = 160.0
FINGER_EXTENDED_RADIAL_RATIO = 1.10
FINGER_FOLDED_ANGLE = 125.0
FINGER_FOLDED_RADIAL_RATIO = 1.02
THUMB_EXTENDED_ANGLE = 150.0
THUMB_EXTENDED_DISTANCE_RATIO = 0.45
THUMB_FOLDED_DISTANCE_RATIO = 0.35
PINCH_ENTER_RATIO = 0.35
PINCH_RELEASE_RATIO = 0.50
STABLE_OBSERVATIONS = 3
CURSOR_EMA_ALPHA = 0.35


def validate_python_version(version: tuple[int, int] | None = None) -> None:
    actual = version or (sys.version_info.major, sys.version_info.minor)
    if actual != REQUIRED_PYTHON:
        raise RuntimeError(
            f"GestureCam requires Python 3.12.x; found {actual[0]}.{actual[1]}. "
            "Create the environment with: py -3.12 -m venv .venv"
        )


def validate_model_asset(path: Path = MODEL_PATH) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(
            f"Hand Landmarker model is missing or empty: {path}\n"
            "Run the model download command from README.md, then start GestureCam again."
        )
    return path
