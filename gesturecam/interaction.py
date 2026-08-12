from __future__ import annotations

from enum import Enum, auto

from .config import HAND_LOSS_GRACE_MS, MIN_SELECTION_HEIGHT_PX, MIN_SELECTION_WIDTH_PX
from .geometry import Point, Rect, clamp_cube_rect, rect_to_pixel_bounds
from .gestures import Gesture, GestureUpdate


class EffectMode(Enum):
    BLUR = auto()
    CUBE = auto()


class InteractionState(Enum):
    READY = auto()
    SELECTING = auto()
    DRAGGING_OBJECT = auto()
    HAND_LOST = auto()


class InteractionController:
    def __init__(self) -> None:
        self.mode = EffectMode.BLUR
        self.state = InteractionState.READY
        self.blur_rect: Rect | None = None
        self.cube_rect: Rect | None = None
        self.selection_anchor: Point | None = None
        self.preview_rect: Rect | None = None
        self.grab_offset: Point | None = None
        self.original_cube_rect: Rect | None = None
        self._prior_active_state: InteractionState | None = None
        self._hand_lost_since_ms: float | None = None
        self.shutdown_requested = False

    def handle_key(self, key: int | str | None) -> None:
        normalized = self._normalize_key(key)
        if normalized == "q":
            self.shutdown_requested = True
        elif normalized == "escape":
            if self.state is InteractionState.READY:
                self.shutdown_requested = True
            else:
                self._cancel_active()
        elif self.state is InteractionState.READY and normalized in {"b", "c"}:
            self.mode = EffectMode.BLUR if normalized == "b" else EffectMode.CUBE

    def process(
        self,
        update: GestureUpdate | None,
        cursor: Point | None,
        pinch_active: bool,
        hand_present: bool,
        now_ms: float,
        frame_size: tuple[int, int],
    ) -> None:
        if not hand_present or cursor is None:
            self._handle_hand_missing(now_ms)
            return
        if self.state is InteractionState.HAND_LOST and not self._resume_after_loss(now_ms, pinch_active):
            return
        if update is None:
            return
        if update.entered is Gesture.FIST:
            self._handle_fist()
            return
        if self.state is InteractionState.READY:
            self._process_ready(update, cursor)
        elif self.state is InteractionState.SELECTING:
            self._process_selection(update, cursor, pinch_active, frame_size)
        elif self.state is InteractionState.DRAGGING_OBJECT:
            self._process_drag(update, cursor, pinch_active, frame_size)

    def _process_ready(self, update: GestureUpdate, cursor: Point) -> None:
        if update.entered is not Gesture.PINCH:
            return
        if self.mode is EffectMode.CUBE and self.cube_rect is not None and self.cube_rect.contains(cursor):
            self.state = InteractionState.DRAGGING_OBJECT
            self.original_cube_rect = self.cube_rect
            self.grab_offset = (cursor[0] - self.cube_rect.left, cursor[1] - self.cube_rect.top)
            return
        self.state = InteractionState.SELECTING
        self.selection_anchor = cursor
        self.preview_rect = Rect.from_points(cursor, cursor)

    def _process_selection(
        self,
        update: GestureUpdate,
        cursor: Point,
        pinch_active: bool,
        frame_size: tuple[int, int],
    ) -> None:
        if pinch_active and self.selection_anchor is not None:
            self.preview_rect = Rect.from_points(self.selection_anchor, cursor)
        if update.released is not Gesture.PINCH:
            return
        if self.preview_rect is not None and self._selection_valid(self.preview_rect, frame_size):
            if self.mode is EffectMode.BLUR:
                self.blur_rect = self.preview_rect
            else:
                width, height = frame_size
                self.cube_rect = clamp_cube_rect(
                    self.preview_rect,
                    self.preview_rect.left,
                    self.preview_rect.top,
                    width,
                    height,
                )
        self._clear_active()

    def _process_drag(
        self,
        update: GestureUpdate,
        cursor: Point,
        pinch_active: bool,
        frame_size: tuple[int, int],
    ) -> None:
        if pinch_active and self.cube_rect is not None and self.grab_offset is not None:
            width, height = frame_size
            desired_left = cursor[0] - self.grab_offset[0]
            desired_top = cursor[1] - self.grab_offset[1]
            self.cube_rect = clamp_cube_rect(self.cube_rect, desired_left, desired_top, width, height)
        if update.released is Gesture.PINCH:
            self._clear_active()

    def _handle_fist(self) -> None:
        if self.state is not InteractionState.READY:
            self._cancel_active()
        elif self.mode is EffectMode.BLUR:
            self.blur_rect = None
        else:
            self.cube_rect = None

    def _handle_hand_missing(self, now_ms: float) -> None:
        if self.state in {InteractionState.SELECTING, InteractionState.DRAGGING_OBJECT}:
            self._prior_active_state = self.state
            self._hand_lost_since_ms = now_ms
            self.state = InteractionState.HAND_LOST
        elif self.state is InteractionState.HAND_LOST and self._loss_expired(now_ms):
            self._cancel_active()

    def _resume_after_loss(self, now_ms: float, pinch_active: bool) -> bool:
        if self._loss_expired(now_ms) or not pinch_active or self._prior_active_state is None:
            self._cancel_active()
            return False
        self.state = self._prior_active_state
        self._hand_lost_since_ms = None
        self._prior_active_state = None
        return True

    def _loss_expired(self, now_ms: float) -> bool:
        return self._hand_lost_since_ms is not None and now_ms - self._hand_lost_since_ms >= HAND_LOSS_GRACE_MS

    def _selection_valid(self, rect: Rect, frame_size: tuple[int, int]) -> bool:
        left, top, right, bottom = rect_to_pixel_bounds(rect, *frame_size)
        return right - left >= MIN_SELECTION_WIDTH_PX and bottom - top >= MIN_SELECTION_HEIGHT_PX

    def _cancel_active(self) -> None:
        dragging = self.state is InteractionState.DRAGGING_OBJECT or (
            self.state is InteractionState.HAND_LOST
            and self._prior_active_state is InteractionState.DRAGGING_OBJECT
        )
        if dragging and self.original_cube_rect is not None:
            self.cube_rect = self.original_cube_rect
        self._clear_active()

    def _clear_active(self) -> None:
        self.state = InteractionState.READY
        self.selection_anchor = None
        self.preview_rect = None
        self.grab_offset = None
        self.original_cube_rect = None
        self._prior_active_state = None
        self._hand_lost_since_ms = None

    @staticmethod
    def _normalize_key(key: int | str | None) -> str | None:
        if isinstance(key, str):
            return key.lower()
        if key == 27:
            return "escape"
        if isinstance(key, int) and 0 <= key <= 255:
            return chr(key).lower()
        return None
