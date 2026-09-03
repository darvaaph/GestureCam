from __future__ import annotations

import argparse
import sys

if sys.version_info[:2] != (3, 12):
    print(
        f"GestureCam requires Python 3.12.x; found {sys.version_info.major}.{sys.version_info.minor}. "
        "Create the environment with: py -3.12 -m venv .venv",
        file=sys.stderr,
    )
    raise SystemExit(1)

import time
from collections import deque

import cv2

from .camera import Camera
from .config import MODEL_PATH, WINDOW_NAME, validate_model_asset, validate_python_version
from .effects import apply_full_frame_blur, draw_landmarks, draw_status
from .gestures import Gesture, GestureStabilizer, RawGestureRecognizer
from .hand_tracking import HandTracker


def _rolling_fps(samples: deque[float]) -> float:
    if len(samples) < 2:
        return 0.0
    elapsed = samples[-1] - samples[0]
    return (len(samples) - 1) / elapsed if elapsed > 0.0 else 0.0


def _window_closed() -> bool:
    try:
        return cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def should_blur(stable_gestures: list[Gesture]) -> bool:
    return Gesture.PEACE in stable_gestures


def _show_startup_frame(camera: Camera) -> None:
    frame = camera.read()
    while frame is None:
        frame = camera.read()
    output = cv2.flip(frame, 1)
    cv2.rectangle(output, (0, 0), (330, 48), (25, 25, 25), -1)
    cv2.putText(
        output,
        "Starting hand tracker...",
        (12, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (245, 245, 245),
        1,
        cv2.LINE_AA,
    )
    cv2.imshow(WINDOW_NAME, output)
    cv2.waitKey(1)


def _run_loop(camera: Camera, tracker: HandTracker) -> int:
    recognizers = [RawGestureRecognizer(), RawGestureRecognizer()]
    stabilizers = [GestureStabilizer(), GestureStabilizer()]
    frame_times: deque[float] = deque(maxlen=60)

    while True:
        try:
            frame = camera.read()
        except RuntimeError as exc:
            print(f"GestureCam: {exc}", file=sys.stderr)
            return 1
        if frame is None:
            continue

        mirrored = cv2.flip(frame, 1)
        now = time.perf_counter()
        frame_times.append(now)
        hands = tracker.detect(mirrored, int(now * 1000.0))
        stable_gestures: list[Gesture] = []
        for index, landmarks in enumerate(hands):
            raw_gesture = recognizers[index].classify(landmarks)
            stable_gesture = stabilizers[index].update(
                raw_gesture,
                recognizers[index].pinch_release_observation,
            ).stable_gesture
            stable_gestures.append(stable_gesture)
        for index in range(len(hands), 2):
            recognizers[index] = RawGestureRecognizer()
            stabilizers[index] = GestureStabilizer()

        output = mirrored.copy()
        if should_blur(stable_gestures):
            apply_full_frame_blur(output)
        for landmarks in hands:
            draw_landmarks(output, landmarks)
        draw_status(
            output,
            stable_gestures,
            len(hands),
            _rolling_fps(frame_times),
            camera.camera_index,
        )
        cv2.imshow(WINDOW_NAME, output)

        key = cv2.waitKey(1)
        if key >= 0 and (key & 0xFF) in {27, ord("q"), ord("Q")}:
            return 0
        if _window_closed():
            return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Blur the webcam when an open palm is detected")
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        metavar="INDEX",
        help="camera device index passed to OpenCV VideoCapture (default: 0)",
    )
    args = parser.parse_args(argv)
    if args.camera < 0:
        parser.error("--camera must be zero or a positive integer")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        validate_python_version()
        model_path = validate_model_asset(MODEL_PATH)
    except RuntimeError as exc:
        print(f"GestureCam: {exc}", file=sys.stderr)
        return 1

    camera = Camera(camera_index=args.camera)
    tracker: HandTracker | None = None
    try:
        try:
            camera.open()
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            _show_startup_frame(camera)
            tracker = HandTracker(model_path)
        except RuntimeError as exc:
            print(f"GestureCam: {exc}", file=sys.stderr)
            return 1
        return _run_loop(camera, tracker)
    finally:
        if tracker is not None:
            tracker.close()
        camera.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
