import pytest

from gesturecam.geometry import Rect
from gesturecam.gestures import Gesture, GestureUpdate
from gesturecam.interaction import EffectMode, InteractionController, InteractionState

FRAME = (200, 100)
PINCH_ENTER = GestureUpdate(Gesture.PINCH, entered=Gesture.PINCH)
PINCH_HOLD = GestureUpdate(Gesture.PINCH, held=True)
PINCH_RELEASE = GestureUpdate(Gesture.UNKNOWN, released=Gesture.PINCH)
FIST_ENTER = GestureUpdate(Gesture.FIST, entered=Gesture.FIST)
FIST_HOLD = GestureUpdate(Gesture.FIST, held=True)
OPEN_ENTER = GestureUpdate(Gesture.OPEN_PALM, entered=Gesture.OPEN_PALM)


def observe(controller, update, cursor=(0.2, 0.3), pinch=False, present=True, now=0.0):
    controller.process(update, cursor, pinch, present, now, FRAME)


def make_selection(controller, end=(0.7, 0.8)):
    observe(controller, PINCH_ENTER, (0.1, 0.2), True)
    observe(controller, PINCH_HOLD, end, True)


def test_ready_mode_keys_preserve_effects() -> None:
    controller = InteractionController()
    controller.blur_rect = Rect(0.1, 0.1, 0.4, 0.4)
    controller.cube_rect = Rect(0.2, 0.3, 0.5, 0.6)
    controller.handle_key("C")
    assert controller.mode is EffectMode.CUBE
    assert controller.blur_rect is not None and controller.cube_rect is not None
    controller.handle_key("b")
    assert controller.mode is EffectMode.BLUR


def test_pinch_outside_cube_or_without_cube_starts_selection() -> None:
    controller = InteractionController()
    observe(controller, PINCH_ENTER, (0.1, 0.2), True)
    assert controller.state is InteractionState.SELECTING
    assert controller.selection_anchor == (0.1, 0.2)


def test_pinch_outside_existing_cube_starts_replacement_selection() -> None:
    controller = InteractionController()
    controller.mode = EffectMode.CUBE
    controller.cube_rect = Rect(0.4, 0.4, 0.7, 0.7)
    observe(controller, PINCH_ENTER, (0.1, 0.2), True)
    assert controller.state is InteractionState.SELECTING
    assert controller.original_cube_rect is None


def test_pinch_inside_cube_starts_drag_and_preserves_offset() -> None:
    controller = InteractionController()
    controller.mode = EffectMode.CUBE
    controller.cube_rect = Rect(0.2, 0.3, 0.5, 0.6)
    observe(controller, PINCH_ENTER, (0.3, 0.4), True)
    assert controller.state is InteractionState.DRAGGING_OBJECT
    assert controller.grab_offset == pytest.approx((0.1, 0.1))


def test_idle_fist_deletes_only_current_mode_and_hold_does_not_repeat() -> None:
    controller = InteractionController()
    original_cube = Rect(0.2, 0.3, 0.5, 0.6)
    controller.blur_rect = Rect(0.1, 0.1, 0.4, 0.4)
    controller.cube_rect = original_cube
    observe(controller, FIST_ENTER)
    assert controller.blur_rect is None
    assert controller.cube_rect == original_cube
    controller.blur_rect = Rect(0.15, 0.15, 0.45, 0.45)
    observe(controller, FIST_HOLD)
    assert controller.blur_rect is not None


def test_open_palm_is_neutral() -> None:
    controller = InteractionController()
    controller.blur_rect = Rect(0.1, 0.1, 0.4, 0.4)
    observe(controller, OPEN_ENTER)
    assert controller.state is InteractionState.READY
    assert controller.blur_rect is not None


def test_selection_hold_updates_preview_and_valid_release_commits() -> None:
    controller = InteractionController()
    make_selection(controller)
    assert controller.preview_rect == Rect(0.1, 0.2, 0.7, 0.8)
    observe(controller, PINCH_RELEASE, (0.7, 0.8), False)
    assert controller.state is InteractionState.READY
    assert controller.blur_rect == Rect(0.1, 0.2, 0.7, 0.8)


def test_invalid_selection_does_not_replace_prior_effect() -> None:
    controller = InteractionController()
    prior = Rect(0.1, 0.1, 0.5, 0.5)
    controller.blur_rect = prior
    make_selection(controller, (0.15, 0.25))
    observe(controller, PINCH_RELEASE, (0.15, 0.25), False)
    assert controller.blur_rect == prior


def test_new_selection_replaces_only_current_modes_effect() -> None:
    controller = InteractionController()
    cube = Rect(0.2, 0.3, 0.5, 0.6)
    controller.cube_rect = cube
    controller.blur_rect = Rect(0.0, 0.0, 0.3, 0.4)
    make_selection(controller, (0.8, 0.9))
    observe(controller, PINCH_RELEASE, (0.8, 0.9), False)
    assert controller.blur_rect == Rect(0.1, 0.2, 0.8, 0.9)
    assert controller.cube_rect == cube


def test_valid_cube_selection_replaces_cube_and_preserves_blur() -> None:
    controller = InteractionController()
    controller.mode = EffectMode.CUBE
    blur = Rect(0.0, 0.0, 0.3, 0.4)
    controller.blur_rect = blur
    controller.cube_rect = Rect(0.2, 0.3, 0.5, 0.6)
    make_selection(controller, (0.8, 0.9))
    observe(controller, PINCH_RELEASE, (0.8, 0.9), False)
    assert controller.cube_rect != Rect(0.2, 0.3, 0.5, 0.6)
    assert controller.blur_rect == blur


def test_idle_fist_deletes_cube_in_cube_mode() -> None:
    controller = InteractionController()
    controller.mode = EffectMode.CUBE
    controller.blur_rect = Rect(0.1, 0.1, 0.4, 0.4)
    controller.cube_rect = Rect(0.2, 0.3, 0.5, 0.6)
    observe(controller, FIST_ENTER)
    assert controller.cube_rect is None
    assert controller.blur_rect is not None


@pytest.mark.parametrize("cancel", [FIST_ENTER, "escape"])
def test_fist_or_escape_cancels_selection(cancel) -> None:
    controller = InteractionController()
    make_selection(controller)
    if isinstance(cancel, str):
        controller.handle_key(cancel)
    else:
        observe(controller, cancel)
    assert controller.state is InteractionState.READY
    assert controller.preview_rect is None
    assert controller.blur_rect is None


def test_mode_change_during_active_interaction_is_ignored() -> None:
    controller = InteractionController()
    make_selection(controller)
    controller.handle_key("c")
    assert controller.mode is EffectMode.BLUR
    assert controller.state is InteractionState.SELECTING


def test_hand_loss_during_selection_resumes_inside_grace() -> None:
    controller = InteractionController()
    make_selection(controller)
    observe(controller, None, cursor=None, present=False, now=100.0)
    assert controller.state is InteractionState.HAND_LOST
    observe(controller, PINCH_HOLD, (0.8, 0.8), True, True, 300.0)
    assert controller.state is InteractionState.SELECTING
    assert controller.preview_rect == Rect(0.1, 0.2, 0.8, 0.8)


def test_hand_loss_expiry_discards_selection() -> None:
    controller = InteractionController()
    make_selection(controller)
    observe(controller, None, cursor=None, present=False, now=100.0)
    observe(controller, None, cursor=None, present=False, now=350.0)
    assert controller.state is InteractionState.READY
    assert controller.preview_rect is None
    assert controller.blur_rect is None


def test_cube_drag_moves_without_snap_and_release_commits() -> None:
    controller = InteractionController()
    controller.mode = EffectMode.CUBE
    controller.cube_rect = Rect(0.2, 0.3, 0.5, 0.6)
    observe(controller, PINCH_ENTER, (0.3, 0.4), True)
    observe(controller, PINCH_HOLD, (0.6, 0.7), True)
    moved = controller.cube_rect
    assert moved is not None
    assert moved.left == pytest.approx(0.5)
    assert moved.top == pytest.approx(0.6)
    observe(controller, PINCH_RELEASE, (0.6, 0.7), False)
    assert controller.state is InteractionState.READY
    assert controller.cube_rect == moved


@pytest.mark.parametrize("cancel", [FIST_ENTER, "escape"])
def test_fist_or_escape_rolls_back_cube_drag(cancel) -> None:
    controller = InteractionController()
    controller.mode = EffectMode.CUBE
    original = Rect(0.2, 0.3, 0.5, 0.6)
    controller.cube_rect = original
    observe(controller, PINCH_ENTER, (0.3, 0.4), True)
    observe(controller, PINCH_HOLD, (0.6, 0.7), True)
    if isinstance(cancel, str):
        controller.handle_key(cancel)
    else:
        observe(controller, cancel)
    assert controller.state is InteractionState.READY
    assert controller.cube_rect == original


def test_cube_hand_loss_resumes_within_grace_and_expiry_rolls_back() -> None:
    controller = InteractionController()
    controller.mode = EffectMode.CUBE
    original = Rect(0.2, 0.3, 0.5, 0.6)
    controller.cube_rect = original
    observe(controller, PINCH_ENTER, (0.3, 0.4), True)
    observe(controller, PINCH_HOLD, (0.6, 0.7), True)
    observe(controller, None, cursor=None, present=False, now=100.0)
    observe(controller, PINCH_HOLD, (0.65, 0.7), True, True, 300.0)
    assert controller.state is InteractionState.DRAGGING_OBJECT
    observe(controller, None, cursor=None, present=False, now=400.0)
    observe(controller, None, cursor=None, present=False, now=650.0)
    assert controller.state is InteractionState.READY
    assert controller.cube_rect == original


def test_hand_return_without_pinch_cancels_active_interaction() -> None:
    controller = InteractionController()
    make_selection(controller)
    observe(controller, None, cursor=None, present=False, now=100.0)
    observe(controller, PINCH_RELEASE, (0.7, 0.8), False, True, 200.0)
    assert controller.state is InteractionState.READY
    assert controller.blur_rect is None


def test_fist_wins_over_simultaneous_pinch_release() -> None:
    controller = InteractionController()
    make_selection(controller)
    simultaneous = GestureUpdate(Gesture.FIST, entered=Gesture.FIST, released=Gesture.PINCH)
    observe(controller, simultaneous, (0.7, 0.8), False)
    assert controller.blur_rect is None
    assert controller.state is InteractionState.READY


@pytest.mark.parametrize(
    "state",
    [
        InteractionState.READY,
        InteractionState.SELECTING,
        InteractionState.DRAGGING_OBJECT,
        InteractionState.HAND_LOST,
    ],
)
def test_q_requests_shutdown_from_every_state(state) -> None:
    controller = InteractionController()
    controller.state = state
    controller.handle_key("Q")
    assert controller.shutdown_requested


def test_idle_escape_requests_shutdown() -> None:
    controller = InteractionController()
    controller.handle_key(27)
    assert controller.shutdown_requested
