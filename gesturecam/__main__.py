from __future__ import annotations

import sys

if sys.version_info[:2] != (3, 12):
    print(
        f"GestureCam requires Python 3.12.x; found {sys.version_info.major}.{sys.version_info.minor}. "
        "Create the environment with: py -3.12 -m venv .venv",
        file=sys.stderr,
    )
    raise SystemExit(1)

import time
import argparse
from collections import deque

import cv2

from .camera import Camera
from .config import (
    HAND_LOSS_GRACE_MS,
    MODEL_PATH,
    WINDOW_NAME,
    validate_model_asset,
    validate_python_version,
)
from .effects import (
    apply_blur,
    apply_full_frame_blur,
    draw_cube,
    draw_cursor,
    draw_landmarks,
    draw_selection,
    draw_status,
)
from .gestures import CursorSmoother, Gesture, GestureStabilizer, RawGestureRecognizer
from .hand_tracking import HandTracker
from .interaction import InteractionController


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


def _show_startup_frame(camera: Camera) -> None:
    frame = camera.read()
    while frame is None:
        frame = camera.read()
    output = cv2.flip(frame, 1)
    cv2.rectangle(output, (0, 0), (370, 48), (25, 25, 25), -1)
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
    recognizer = RawGestureRecognizer()
    stabilizer = GestureStabilizer()
    smoother = CursorSmoother()
    controller = InteractionController()
    frame_times: deque[float] = deque(maxlen=60)
    hand_absent_since: float | None = None

    while not controller.shutdown_requested:
        try:
            frame = camera.read()
        except RuntimeError as exc:
            print(f"GestureCam: {exc}", file=sys.stderr)
            return 1
        if frame is None:
            continue

        mirrored = cv2.flip(frame, 1)
        now = time.perf_counter()
        now_ms = now * 1000.0
        frame_times.append(now)
        landmarks = tracker.detect(mirrored, int(now_ms))
        hand_present = landmarks is not None
        cursor = None
        update = None

        if landmarks is not None:
            hand_absent_since = None
            raw_gesture = recognizer.classify(landmarks)
            update = stabilizer.update(raw_gesture, recognizer.pinch_release_observation)
            cursor = smoother.update(landmarks, recognizer.pinch_active)
        else:
            hand_absent_since = hand_absent_since or now_ms
            if now_ms - hand_absent_since >= HAND_LOSS_GRACE_MS:
                smoother.reset()

        height, width = mirrored.shape[:2]
        controller.process(
            update,
            cursor,
            recognizer.pinch_active,
            hand_present,
            now_ms,
            (width, height),
        )

        output = mirrored.copy()
        if hand_present and stabilizer.stable_gesture is Gesture.OPEN_PALM:
            apply_full_frame_blur(output)
        else:
            apply_blur(output, controller.blur_rect)
        draw_cube(output, controller.cube_rect)
        draw_selection(output, controller.preview_rect)
        if landmarks is not None:
            draw_landmarks(output, landmarks)
        draw_cursor(output, cursor, recognizer.pinch_active)
        draw_status(
            output,
            controller,
            stabilizer.stable_gesture,
            hand_present,
            _rolling_fps(frame_times),
            camera.camera_index,
        )
        cv2.imshow(WINDOW_NAME, output)

        key = cv2.waitKey(1)
        controller.handle_key(key & 0xFF if key >= 0 else None)
        if _window_closed():
            controller.shutdown_requested = True
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GestureCam webcam gesture prototype")
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
