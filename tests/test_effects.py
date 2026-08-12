from pathlib import Path

import cv2
import numpy as np
import pytest

import gesturecam.__main__ as app
from gesturecam.camera import Camera
from gesturecam.config import MAX_CONSECUTIVE_READ_FAILURES, validate_model_asset, validate_python_version
from gesturecam.effects import apply_blur, apply_full_frame_blur, draw_cube, draw_selection
from gesturecam.geometry import Rect, cube_depth_px, rect_to_pixel_bounds


def test_blur_changes_pixels_only_inside_roi() -> None:
    random = np.random.default_rng(4)
    frame = random.integers(0, 256, (60, 80, 3), dtype=np.uint8)
    original = frame.copy()
    rect = Rect(0.25, 0.25, 0.75, 0.75)
    apply_blur(frame, rect)
    left, top, right, bottom = rect_to_pixel_bounds(rect, 80, 60)
    outside = np.ones(frame.shape[:2], dtype=bool)
    outside[top:bottom, left:right] = False
    assert np.array_equal(frame[outside], original[outside])
    assert not np.array_equal(frame[top:bottom, left:right], original[top:bottom, left:right])


def test_full_frame_blur_changes_entire_camera_frame() -> None:
    random = np.random.default_rng(8)
    frame = random.integers(0, 256, (60, 80, 3), dtype=np.uint8)
    original = frame.copy()
    result = apply_full_frame_blur(frame)
    assert result is frame
    assert np.count_nonzero(frame != original) > frame.size * 0.95


def test_full_frame_blur_accepts_empty_frame() -> None:
    frame = np.empty((0, 0, 3), dtype=np.uint8)
    assert apply_full_frame_blur(frame) is frame


@pytest.mark.parametrize("rect", [None, Rect(1.2, 1.2, 1.4, 1.4), Rect(0.5, 0.5, 0.5, 0.5)])
def test_empty_or_clamped_invalid_blur_is_unchanged(rect) -> None:
    frame = np.arange(300, dtype=np.uint8).reshape(10, 10, 3)
    original = frame.copy()
    assert np.array_equal(apply_blur(frame, rect), original)


def test_cube_depth_respects_minimum_and_maximum() -> None:
    assert cube_depth_px(Rect(0.1, 0.1, 0.12, 0.12), 1000, 1000) == 12
    assert cube_depth_px(Rect(0.1, 0.1, 0.9, 0.9), 1000, 1000) == 40


def test_cube_and_selection_render_at_frame_boundaries() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    touching = Rect(0.0, 0.0, 1.0, 1.0)
    draw_cube(frame, touching)
    draw_selection(frame, touching)
    assert np.count_nonzero(frame) > 0


class FakeCapture:
    def __init__(self, opened=True, reads=None):
        self.opened = opened
        self.reads = list(reads or [])
        self.released = False
        self.settings = []

    def isOpened(self):
        return self.opened

    def set(self, key, value):
        self.settings.append((key, value))
        return True

    def read(self):
        return self.reads.pop(0) if self.reads else (False, None)

    def release(self):
        self.released = True


def test_camera_open_failure_is_actionable_and_releases() -> None:
    capture = FakeCapture(opened=False)
    camera = Camera(lambda _: capture, camera_index=3)
    with pytest.raises(RuntimeError, match="Camera index 3"):
        camera.open()
    assert capture.released


def test_one_camera_read_failure_is_tolerated() -> None:
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    capture = FakeCapture(reads=[(False, None), (True, frame)])
    camera = Camera(lambda _: capture)
    camera.open()
    assert camera.read() is None
    assert camera.read() is frame
    camera.close()
    assert capture.released


def test_selected_camera_index_is_passed_to_opencv() -> None:
    selected = []
    camera = Camera(lambda index: selected.append(index) or FakeCapture(), camera_index=2)
    camera.open()
    camera.close()
    assert selected == [2]


def test_thirty_camera_failures_request_controlled_shutdown() -> None:
    capture = FakeCapture()
    camera = Camera(lambda _: capture)
    camera.open()
    for _ in range(MAX_CONSECUTIVE_READ_FAILURES - 1):
        assert camera.read() is None
    with pytest.raises(RuntimeError, match="30 consecutive"):
        camera.read()


def test_camera_context_cleans_up_normally_and_on_exception() -> None:
    normal_capture = FakeCapture()
    with Camera(lambda _: normal_capture):
        pass
    assert normal_capture.released

    error_capture = FakeCapture()
    with pytest.raises(ValueError):
        with Camera(lambda _: error_capture):
            raise ValueError("controlled test failure")
    assert error_capture.released


def test_startup_validations_are_actionable(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="requires Python 3.12"):
        validate_python_version((3, 14))
    with pytest.raises(RuntimeError, match="model is missing or empty"):
        validate_model_asset(tmp_path / "missing.task")
    empty = tmp_path / "empty.task"
    empty.touch()
    with pytest.raises(RuntimeError, match="model is missing or empty"):
        validate_model_asset(empty)


class FakeCameraSession:
    def __init__(self, failure=False):
        self.camera_index = 0
        self.failure = failure
        self.opened = False
        self.closed = False
        self.read_count = 0

    def open(self):
        self.opened = True

    def read(self):
        if self.failure:
            raise RuntimeError("controlled stream failure")
        self.read_count += 1
        return np.zeros((80, 120, 3), dtype=np.uint8)

    def close(self):
        self.closed = True


class FakeTracker:
    def __init__(self):
        self.closed = False

    def detect(self, frame, timestamp):
        return None

    def close(self):
        self.closed = True


def patch_display(monkeypatch, key=ord("q")):
    monkeypatch.setattr(cv2, "namedWindow", lambda *args: None)
    monkeypatch.setattr(cv2, "imshow", lambda *args: None)
    monkeypatch.setattr(cv2, "waitKey", lambda _: key)
    monkeypatch.setattr(cv2, "getWindowProperty", lambda *args: 1.0)
    monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)


def test_main_loop_cleans_resources_on_normal_exit(monkeypatch) -> None:
    camera = FakeCameraSession()
    tracker = FakeTracker()
    monkeypatch.setattr(
        app,
        "Camera",
        lambda camera_index: setattr(camera, "camera_index", camera_index) or camera,
    )
    monkeypatch.setattr(app, "HandTracker", lambda _: tracker)
    patch_display(monkeypatch)
    assert app.main(["--camera", "2"]) == 0
    assert camera.camera_index == 2
    assert camera.opened and camera.closed and tracker.closed


def test_main_loop_cleans_resources_on_controlled_error(monkeypatch, capsys) -> None:
    camera = FakeCameraSession()
    tracker = FakeTracker()

    def tracker_after_startup(_):
        camera.failure = True
        return tracker

    monkeypatch.setattr(
        app,
        "Camera",
        lambda camera_index: setattr(camera, "camera_index", camera_index) or camera,
    )
    monkeypatch.setattr(app, "HandTracker", tracker_after_startup)
    patch_display(monkeypatch)
    assert app.main(["--camera", "1"]) == 1
    assert "controlled stream failure" in capsys.readouterr().err
    assert camera.closed and tracker.closed
