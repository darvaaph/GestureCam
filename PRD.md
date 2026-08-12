# GestureCam — Technical Product Requirements Document

**Status:** Ready for implementation  
**Document version:** 1.0  
**Target:** MVP desktop prototype for Windows 10/11 64-bit  
**Runtime:** CPython 3.12.x  
**Primary audience:** Coding agent implementing the repository end to end

---

## 1. Document contract

This document is the implementation source of truth for the GestureCam MVP. The coding agent must implement the smallest clean solution that satisfies it. When a detail is not specified, choose the simplest reversible option consistent with the guardrails in this document. Do not add “helpful” features, layers, dependencies, or redesigns beyond the acceptance criteria.

Normative terms:

- **MUST / MUST NOT**: required for MVP acceptance.
- **SHOULD / SHOULD NOT**: expected unless a concrete technical constraint is documented.
- **MAY**: optional and must not delay or complicate the MVP.

If implementation reveals a genuine contradiction, document it in `README.md`, choose the lower-complexity interpretation, and keep the change narrow. Do not silently change product behavior.

---

## 2. Product summary

GestureCam is a local desktop computer-vision prototype. It displays a mirrored webcam feed, tracks one hand, recognizes four deterministic hand gestures, and lets the user manipulate two visual effects in real time:

1. Select a rectangular area with a pinch-and-drag gesture and blur it.
2. Draw a rectangle that becomes an OpenCV-rendered pseudo-3D cube, then move the cube with pinch-and-drag.

The MVP proves the complete interaction loop:

```text
webcam frame
    -> one-hand landmarks
    -> deterministic gesture
    -> debounced interaction event
    -> explicit state transition
    -> visual effect
    -> displayed frame and feedback
```

It is a prototype, not a production AR system, gesture platform, or 3D application.

---

## 3. Problem and intended outcome

Raw hand tracking is not sufficient for a usable interaction. Frame-level classifications can flicker, coordinates can jitter, and a pinch persists across multiple frames. GestureCam must convert noisy observations into stable start/hold/release events and make those events visibly control effects.

The MVP is successful when a user with a functioning webcam can:

- launch the application locally;
- see a mirrored 1280 × 720 camera feed;
- see one tracked hand and the currently recognized gesture;
- use the index finger as a smoothed cursor;
- choose Blur or Cube mode with a keyboard key;
- pinch, drag, and release to create the selected effect;
- grab and move the cube with another pinch-and-drag;
- cancel or delete with a fist;
- exit cleanly without leaving the camera locked.

---

## 4. MVP scope

### 4.1 Required capabilities

| ID | Capability | Required behavior |
|---|---|---|
| MVP-01 | Camera | Open the default webcam, request 1280 × 720, mirror the frame horizontally, and show it in one OpenCV window. |
| MVP-02 | Hand tracking | Detect at most one hand and expose 21 normalized landmarks. |
| MVP-03 | Landmark overlay | Draw landmarks/connections when a hand is present. |
| MVP-04 | Gesture recognition | Classify `OPEN_PALM`, `FIST`, `POINTING`, `PINCH`, or `UNKNOWN` with deterministic geometry. |
| MVP-05 | Stability | Debounce gesture changes and smooth cursor coordinates. |
| MVP-06 | Cursor | Show a visible cursor at the index tip, or the thumb/index midpoint while pinching. |
| MVP-07 | Blur selection | In Blur mode, pinch-drag-release creates one persistent rectangular blur region. A new valid blur selection replaces the previous one. |
| MVP-08 | Cube creation | In Cube mode, pinch-drag-release creates one persistent pseudo-3D wireframe cube. A new valid cube replaces the previous one. |
| MVP-09 | Cube movement | Pinching inside the cube's front face grabs it; drag moves it; release commits its new position. |
| MVP-10 | Cancel/delete | A stable fist cancels an active interaction. While idle, a stable fist deletes the effect belonging to the current mode. |
| MVP-11 | Mode selection | `B` selects Blur mode and `C` selects Cube mode. Mode changes are accepted only while idle. |
| MVP-12 | Feedback | Overlay current mode, stable gesture, interaction state, hand status, and rolling FPS. |
| MVP-13 | Graceful lifecycle | Explain camera/model startup failures, survive temporary hand loss, and release all resources on exit. |
| MVP-14 | Tests | Pure geometry, classification, debounce, state transitions, and effect-bound calculations are testable without a webcam. |

### 4.2 Explicit MVP decisions

- Only one hand is processed. If multiple hands are visible, MediaPipe is configured with `num_hands=1`.
- The application uses one OpenCV window. There is no separate GUI framework.
- There is at most one blur region and one cube. This is not an object collection/editor.
- Mode selection uses the keyboard to avoid adding an unreliable gesture-based mode switch.
- The cube is a 2D wireframe with a fixed perspective offset. It is not true 3D.
- Effects exist only for the current process and are not saved.
- All processing is local. The application performs no network requests at runtime.
- Gesture recognition is rule-based. MediaPipe supplies landmarks; it does not supply the four product-level gesture decisions.

---

## 5. User interaction

### 5.1 Controls

| Input | Context | Result |
|---|---|---|
| `B` | `READY` | Switch to Blur mode. |
| `C` | `READY` | Switch to Cube mode. |
| Pinch enter | `READY`, pointer not grabbing cube | Start a rectangular selection at the smoothed pinch midpoint. |
| Pinch hold + movement | Selecting | Update the preview rectangle. |
| Pinch release | Selecting | Commit a valid rectangle; discard an undersized rectangle. |
| Pinch enter inside cube front face | Cube mode, cube exists, `READY` | Start dragging the existing cube while preserving the cursor-to-object offset. |
| Pinch release | Dragging cube | Commit the cube's current position. |
| Stable fist | Selecting/dragging | Cancel and revert the active interaction. |
| Stable fist | `READY` | Delete the blur region in Blur mode or the cube in Cube mode. |
| Open palm | `READY` | Neutral/reset signal only; clear transient hover/candidate feedback, but do not delete committed effects. |
| `Esc` | Active interaction | Cancel the active interaction. |
| `Esc` | `READY` | Exit. |
| `Q` | Any state | Exit cleanly. |

Key handling is case-insensitive. A mode-switch key received during an active interaction is ignored; it must not partially commit or reinterpret the interaction.

### 5.2 On-screen overlay

The overlay MUST remain readable over bright and dark frames. A small filled dark panel or outlined text is acceptable. It contains:

```text
Mode: BLUR | CUBE
Gesture: OPEN_PALM | FIST | POINTING | PINCH | UNKNOWN
State: READY | SELECTING | DRAGGING_OBJECT | HAND_LOST
Hand: DETECTED | NOT DETECTED
FPS: rolling integer
Keys: [B] Blur  [C] Cube  [Esc/Q] Exit
```

During selection, draw the live rectangle and indicate whether its current size is valid. In Cube mode, distinguish the cube's front face enough that the grab hitbox is understandable. Do not add menus, animations, gradients, slogans, onboarding pages, or decorative UI.

---

## 6. Tech stack and dependency policy

### 6.1 Required stack

| Concern | Choice | Usage |
|---|---|---|
| Language | CPython 3.12.x | Project runtime; reject other major/minor versions with a clear setup message. |
| Camera and rendering | OpenCV | Camera capture, mirroring, BGR/RGB conversion, drawing, Gaussian blur, window and keyboard input. |
| Hand landmarks | MediaPipe Hand Landmarker Tasks API | One-hand landmark tracking in `VIDEO` mode with monotonically increasing timestamps. |
| Numerical operations | NumPy | Frame arrays and small vector/geometry operations where it improves clarity. |
| Tests | pytest | Unit and integration-style tests that do not require camera hardware. |

Use the synchronous MediaPipe `VIDEO` API for the MVP. Do not implement application threading or asynchronous callbacks. `detect_for_video` receives a monotonically increasing timestamp in milliseconds. The frame is mirrored before detection so displayed pixels, landmarks, and interaction coordinates use the same coordinate system.

### 6.2 Reproducible baseline

The initial implementation MUST use these direct pinned packages:

`requirements.txt`

```text
mediapipe==0.10.35
opencv-contrib-python==4.12.0.88
numpy==2.2.6
```

`requirements-dev.txt`

```text
-r requirements.txt
pytest==9.1.1
```

Important package rule: MediaPipe depends on the OpenCV contrib distribution, which provides the `cv2` import. Do **not** install `opencv-python`, `opencv-python-headless`, or another OpenCV wheel beside `opencv-contrib-python`; multiple OpenCV distributions share the same `cv2` namespace and can conflict.

Before feature work, the coding agent MUST run a dependency smoke test on Python 3.12 that imports `cv2`, `mediapipe`, and `numpy`, prints their versions, creates the Hand Landmarker, processes a synthetic RGB frame without crashing, and closes it. A pin may be changed only if this smoke test proves the baseline incompatible. If changed, use exact versions, retain Python 3.12, document the reason in `README.md`, and re-run all tests. Do not upgrade merely because a newer version exists.

### 6.3 MediaPipe model asset

The repository uses the official pre-trained Hand Landmarker task bundle:

```text
assets/hand_landmarker.task
```

Download source:

```text
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

The setup instructions MUST include this PowerShell command:

```powershell
New-Item -ItemType Directory -Force assets | Out-Null
Invoke-WebRequest `
  -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" `
  -OutFile "assets\hand_landmarker.task"
```

Do not download the model silently at application runtime. On startup, validate that the asset exists and is non-empty; otherwise exit with the expected path and the setup command. Keep the model source URL in `README.md`. Do not train or modify the model.

### 6.4 MediaPipe configuration defaults

```text
running_mode                  = VIDEO
num_hands                     = 1
min_hand_detection_confidence = 0.60
min_hand_presence_confidence  = 0.60
min_tracking_confidence       = 0.60
```

The tracker returns normalized screen landmarks and handedness. Handedness may be displayed during debugging but is not required by product behavior. World landmarks are not required.

---

## 7. Processing pipeline and data contracts

### 7.1 Per-frame pipeline

The entry point performs these steps in order:

1. Read one BGR frame from the default camera.
2. Mirror it horizontally.
3. Capture a monotonic timestamp and update the FPS tracker.
4. Convert BGR to RGB without unnecessary copies.
5. Wrap the RGB data as a MediaPipe image and call Hand Landmarker in `VIDEO` mode.
6. Convert the first result, if any, into the project's lightweight normalized landmark representation.
7. Compute raw gesture features and a raw gesture.
8. Update temporal gesture stability and cursor smoothing.
9. Feed stable interaction events into the state machine.
10. Apply the committed blur region to the frame.
11. Draw cube, selection preview, landmarks, cursor, and status overlay.
12. Display the frame and handle one keyboard event.

Persistent effect state must not be drawn into the input passed to MediaPipe. Apply effects and overlays only after landmark inference.

### 7.2 Coordinate conventions

- Normalized coordinates use `[0.0, 1.0]` relative to the mirrored frame.
- Pixel coordinates use integer `(x, y)` with origin at the top-left.
- Every normalized-to-pixel conversion clamps to valid frame bounds.
- Rectangles are normalized before use: `left <= right`, `top <= bottom` regardless of drag direction.
- OpenCV array slicing uses an exclusive right/bottom boundary; drawing may use inclusive endpoint pixels. Keep this distinction in one geometry helper.
- Geometry and gesture rules operate on normalized floats. Rendering and ROI slicing operate on clamped pixel integers.

### 7.3 Core value types

Use lightweight dataclasses or named tuples only where they make state explicit. The expected concepts are:

- `Point(x: float, y: float)` or a two-value tuple;
- `Rect(left, top, right, bottom)` with width/height/contains helpers;
- `Gesture` enum;
- `InteractionState` enum;
- `EffectMode` enum;
- `InteractionContext` holding the current mode, state, optional anchor, optional preview, optional committed blur/cube, and drag rollback data.

Do not build a general entity-component system, command bus, event framework, repository layer, or dependency-injection container around these values.

---

## 8. Gesture specification

### 8.1 Landmark indices

Use MediaPipe's standard 21 landmarks:

```text
0  WRIST
1  THUMB_CMC       2  THUMB_MCP       3  THUMB_IP        4  THUMB_TIP
5  INDEX_MCP       6  INDEX_PIP       7  INDEX_DIP       8  INDEX_TIP
9  MIDDLE_MCP     10  MIDDLE_PIP     11  MIDDLE_DIP     12  MIDDLE_TIP
13 RING_MCP       14  RING_PIP       15  RING_DIP       16  RING_TIP
17 PINKY_MCP      18  PINKY_PIP      19  PINKY_DIP      20  PINKY_TIP
```

### 8.2 Scale normalization

Pixel thresholds are forbidden for gesture classification. Define palm scale in normalized coordinates:

```text
palm_scale = max(distance(WRIST, MIDDLE_MCP), epsilon)
```

`epsilon = 1e-6` prevents division by zero. All distance thresholds below are ratios relative to `palm_scale`. This makes recognition less sensitive to camera distance.

### 8.3 Finger posture

For index, middle, ring, and pinky, calculate the 2D angle at PIP using `(MCP, PIP, TIP)` and compare radial distances from the wrist.

An individual non-thumb finger is:

- `EXTENDED` when angle `>= 160°` **and** `distance(TIP, WRIST) >= 1.10 × distance(PIP, WRIST)`;
- `FOLDED` when angle `<= 125°` **or** `distance(TIP, WRIST) <= 1.02 × distance(PIP, WRIST)`;
- `AMBIGUOUS` otherwise.

The thumb is:

- `EXTENDED` when angle at `THUMB_IP` using `(THUMB_MCP, THUMB_IP, THUMB_TIP)` is `>= 150°` and `distance(THUMB_TIP, INDEX_MCP) / palm_scale >= 0.45`;
- `FOLDED` when that ratio is `<= 0.35`;
- `AMBIGUOUS` otherwise.

These are configuration constants, not literals scattered through gesture code. The coding agent may tune thresholds only after recording the original value, test condition, and reason in `README.md` under “Calibration notes.”

### 8.4 Pinch with hysteresis

```text
pinch_ratio = distance(THUMB_TIP, INDEX_TIP) / palm_scale
```

- Raw pinch enters when `pinch_ratio <= 0.35`.
- Once raw pinch is active, it remains active until `pinch_ratio >= 0.50`.
- Values between the two thresholds preserve the prior raw pinch state.

Hysteresis is mandatory. It prevents one threshold boundary from producing rapid pinch/release oscillation.

### 8.5 Raw gesture rules and priority

Evaluate in this exact order; the first matching rule wins:

| Priority | Gesture | Raw rule |
|---:|---|---|
| 1 | `PINCH` | Pinch hysteresis is active. Other finger postures do not matter. |
| 2 | `FIST` | Index, middle, ring, and pinky are all `FOLDED`; pinch is inactive. Thumb may be folded or ambiguous. |
| 3 | `POINTING` | Index is `EXTENDED`; middle, ring, and pinky are `FOLDED`; pinch is inactive. Thumb is ignored. |
| 4 | `OPEN_PALM` | Index, middle, ring, and pinky are all `EXTENDED`; thumb is `EXTENDED`; pinch is inactive. |
| 5 | `UNKNOWN` | No rule above matches, any required landmark is invalid, or a required finger is ambiguous. |

Do not use screen-axis comparisons such as `tip.y < pip.y` as the primary extension rule; they fail when the hand rotates. Do not add gesture-specific ML, gesture recognizer models, training data, or probabilistic voting.

### 8.6 Temporal stability

Maintain a raw candidate, consecutive-observation count, and stable gesture.

- A different non-`UNKNOWN` gesture becomes stable after **3 consecutive processed observations**.
- `UNKNOWN` becomes stable after **3 consecutive observations** but does not trigger an action.
- A stable `PINCH` release event occurs after **3 consecutive non-pinch observations** whose pinch ratio has crossed the release threshold.
- A gesture emits `entered` only once when it becomes stable, `held` while stable, and `released` once when it stops being stable.
- Holding a fist must not repeatedly delete. Deletion is edge-triggered on `FIST entered`, with no repeat until the fist is released and entered again.
- Missing-hand observations do not count as pinch-release observations. Hand absence is handled only by the hand-loss grace rules.
- If `FIST entered` and `PINCH released` become valid on the same observation during an active interaction, fist cancellation has priority and the effect is not committed.

At 24–30 processed observations per second, these rules keep intended gesture latency below 150 ms while suppressing isolated bad frames.

### 8.7 Cursor smoothing

- When stable/raw pinch is active, cursor target is the midpoint of `THUMB_TIP` and `INDEX_TIP`.
- Otherwise, cursor target is `INDEX_TIP`.
- Apply exponential moving average independently to normalized x and y:

```text
smoothed = alpha × current + (1 - alpha) × previous
alpha = 0.35
```

- Initialize the EMA from the first valid point; do not ease in from `(0, 0)`.
- Reset the EMA after the hand has been absent longer than the hand-loss grace period.
- Use smoothed coordinates for cursor and manipulation. Use unsmoothed normalized landmarks for gesture geometry.

---

## 9. Interaction state machine

Gesture classification and interaction state are separate concerns. The gesture detector reports events; it does not mutate effects. The interaction controller owns transitions and committed effect state.

### 9.1 States

| State | Meaning |
|---|---|
| `READY` | No manipulation is active. Mode switches and new interactions are allowed. |
| `SELECTING` | A pinch-drag selection is active. Anchor and current point define a preview rectangle. |
| `DRAGGING_OBJECT` | The existing cube is grabbed. Original rectangle and cursor offset are retained for commit or rollback. |
| `HAND_LOST` | A manipulation was active but no valid hand is currently available within the grace interval. |

No separate “confirmed,” “pinch start,” or “pinch release” states are required; those are events or transition actions, not persistent states.

### 9.2 Constants

```text
HAND_LOSS_GRACE_MS          = 250
MIN_SELECTION_WIDTH_PX      = 30
MIN_SELECTION_HEIGHT_PX     = 30
CURSOR_RADIUS_PX            = 8
CUBE_DEPTH_MIN_PX           = 12
CUBE_DEPTH_MAX_PX           = 40
CUBE_DEPTH_RATIO            = 0.15
BLUR_KERNEL_SIZE            = 31
```

`BLUR_KERNEL_SIZE` must be a positive odd integer. The minimum rectangle is evaluated in pixels using the actual displayed frame dimensions.

### 9.3 Transition table

| Current state | Event/guard | Action | Next state |
|---|---|---|---|
| `READY` | `B` or `C` | Change mode; leave committed effects unchanged. | `READY` |
| `READY` | `PINCH entered`, Cube mode, cube exists, cursor inside cube front face | Save original cube rectangle and cursor-to-top-left offset. | `DRAGGING_OBJECT` |
| `READY` | `PINCH entered` otherwise | Store anchor at smoothed cursor; initialize preview. | `SELECTING` |
| `READY` | `FIST entered` | Delete the committed effect in current mode, if any. | `READY` |
| `READY` | `OPEN_PALM entered` | Clear transient candidate/hover feedback only. | `READY` |
| `SELECTING` | `PINCH held` and hand valid | Update preview endpoint and normalized rectangle. | `SELECTING` |
| `SELECTING` | `PINCH released`, rectangle valid | Replace current mode's committed effect with the normalized rectangle. | `READY` |
| `SELECTING` | `PINCH released`, rectangle invalid | Discard preview; do not change committed effect. | `READY` |
| `SELECTING` | `FIST entered` or `Esc` | Discard preview. | `READY` |
| `SELECTING` | Hand first disappears | Preserve preview and start loss timer. | `HAND_LOST` |
| `DRAGGING_OBJECT` | `PINCH held` and hand valid | Translate cube from cursor minus stored grab offset; clamp it fully inside frame. | `DRAGGING_OBJECT` |
| `DRAGGING_OBJECT` | `PINCH released` | Keep current cube rectangle. | `READY` |
| `DRAGGING_OBJECT` | `FIST entered` or `Esc` | Restore original cube rectangle. | `READY` |
| `DRAGGING_OBJECT` | Hand first disappears | Preserve candidate position and start loss timer. | `HAND_LOST` |
| `HAND_LOST` | Hand returns within 250 ms and pinch remains active | Resume the prior active state without changing anchor/offset. | Prior state |
| `HAND_LOST` | Grace expires while selecting | Discard preview; do not commit. | `READY` |
| `HAND_LOST` | Grace expires while dragging | Restore original cube rectangle. | `READY` |
| Any | `Q` | Begin clean shutdown. | Exit loop |

When the hand disappears while `READY`, remain logically ready and display `Hand: NOT DETECTED`; `HAND_LOST` is only needed to protect an active manipulation.

### 9.4 Selection and effect semantics

#### Blur

- A valid Blur-mode release commits the selected normalized rectangle.
- Apply `cv2.GaussianBlur` only to the selected ROI and write the blurred ROI back to the output frame.
- Skip invalid or empty slices defensively.
- The blur region remains fixed until replaced or deleted.

#### Cube

- A valid Cube-mode release stores the rectangle as the cube's front face.
- Compute depth per render:

```text
depth = clamp(round(0.15 × min(width, height)), 12, 40)
back-face offset = (+depth, -depth)
```

- Clamp creation and movement so both front and back wireframes remain visible. If necessary, reduce depth near frame edges rather than allowing invalid coordinates.
- Draw two rectangles plus four connecting edges. A light transparent face fill is optional only if it adds no dependency or complex blending path.
- Hit testing uses the front rectangle only.
- Grabbing preserves the initial cursor-to-rectangle offset, preventing the cube from snapping its top-left corner to the cursor.

---

## 10. Architecture and folder structure

Use a flat, deliberately small project structure:

```text
GestureCam/
├── assets/
│   └── hand_landmarker.task
├── gesturecam/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── camera.py
│   ├── hand_tracking.py
│   ├── geometry.py
│   ├── gestures.py
│   ├── interaction.py
│   └── effects.py
├── tests/
│   ├── test_geometry.py
│   ├── test_gestures.py
│   ├── test_interaction.py
│   └── test_effects.py
├── .gitignore
├── README.md
├── requirements.txt
└── requirements-dev.txt
```

### 10.1 Module responsibilities

| Module | Responsibility | Must not contain |
|---|---|---|
| `__main__.py` | Dependency wiring, frame loop, key dispatch, shutdown. | Gesture math or effect algorithms. |
| `config.py` | Named constants and one compact immutable settings dataclass if useful. | Environment framework, YAML parsing, or runtime mutation. |
| `camera.py` | Open/read/configure/release camera; actual frame size reporting. | Hand tracking or state machine logic. |
| `hand_tracking.py` | MediaPipe lifecycle, frame conversion contract, landmark extraction. | Product gesture decisions or effect state. |
| `geometry.py` | Pure distance, angle, clamp, rectangle, and coordinate conversion helpers. | OpenCV window or MediaPipe object lifecycle. |
| `gestures.py` | Finger features, pinch hysteresis, raw classification, temporal debounce, cursor EMA. | Camera access or effect mutation. |
| `interaction.py` | Modes, states, transition rules, effect rectangles, cancellation/rollback. | Direct OpenCV drawing or MediaPipe calls. |
| `effects.py` | Apply blur and render selection/cube/cursor/status overlays. | Gesture classification and state transitions. |

Do not create one file per gesture, generic `utils.py`, `managers/`, `services/`, `controllers/`, `interfaces/`, `domain/`, `infrastructure/`, `factories/`, `strategies/`, or `repositories/` directories. A new module is allowed only when an existing module exceeds its hard size budget and the split follows a real responsibility boundary.

---

## 11. Complexity budget

The budget is an acceptance constraint, not a target to maximize.

| Dimension | Budget |
|---|---|
| Production Python modules | 8 including `__init__.py` and `__main__.py`; hard maximum 9 |
| Production source lines | Soft maximum 1,000; hard maximum 1,300, excluding blank lines and generated/vendor code |
| Behavior-rich classes | Maximum 6 |
| Total classes/dataclasses/enums | Maximum 12 |
| Entry points | 1: `python -m gesturecam` |
| Configuration files | No custom config file; use `config.py` only |
| Runtime direct dependencies | 3 distributions: MediaPipe, OpenCV contrib, NumPy |
| Application-created threads/processes | 0 |
| Network/database/cloud | 0 at runtime |
| Persistent effect instances | 1 blur region + 1 cube |
| Custom ML models | 0 |
| Function length | Prefer <= 35 logical lines; hard maximum 60 except the clearly linear frame loop |
| Module length | Prefer <= 200 logical lines; hard maximum 280 |
| Branch complexity | Prefer <= 8 decision points per function |
| Nesting | Maximum 3 levels; use guard clauses |
| Parameters | Prefer <= 5; group truly related immutable settings rather than passing long lists |

If a hard budget must be exceeded to meet a requirement, the coding agent must first demonstrate why a simpler formulation fails and record the exception in `README.md`. “Clean architecture,” future extensibility, and personal preference are not valid reasons.

### 11.1 Earn your abstraction

An abstraction is allowed only when at least one is true:

1. It has two concrete, current call sites with meaningfully shared behavior.
2. It isolates an external resource lifecycle such as camera or MediaPipe.
3. It makes core logic testable without hardware.
4. It represents a required state or value whose invariants would otherwise be duplicated.

Do not introduce an interface for a single implementation, a factory for one constructor, a strategy for two `if` branches, or a base class with no genuine polymorphism.

---

## 12. Code-quality and code-smell guardrails

### 12.1 Required practices

- Prefer small pure functions for geometry, gesture features, and transitions.
- Keep camera and MediaPipe resources behind explicit `open/close` or context-manager lifecycles.
- Release the camera and destroy OpenCV windows in `finally`, even after an exception.
- Use `time.perf_counter()` for elapsed time, timestamps, hand-loss grace, and FPS.
- Use enums for modes, stable gestures, and interaction states; do not compare ad hoc strings throughout the code.
- Use type hints on public functions and state values where they improve comprehension.
- Validate rectangles and clamp all pixel coordinates before slicing.
- Make thresholds named constants in one place.
- Use clear names from this document: `pinch_ratio`, `palm_scale`, `selection_anchor`, `stable_gesture`, `grab_offset`.
- Comments explain why a non-obvious threshold, ordering, or workaround exists; names and code explain what happens.
- Log only lifecycle events, warnings, and errors. Per-frame debug output is forbidden by default.
- Fix root causes. Do not hide timing, coordinate, or lifecycle bugs with broad exception handlers.

### 12.2 Rejected smells

The implementation is not acceptable if it contains:

- mutable module-level application state;
- a god class or a `__main__.py` containing gesture/effect implementations;
- giant `try/except Exception: pass` blocks;
- silent fallbacks that conceal missing camera/model/dependencies;
- duplicated distance, angle, rectangle normalization, or coordinate-clamping logic;
- magic thresholds repeated in multiple modules;
- boolean parameter chains that obscure state;
- deep nested `if` trees instead of an explicit transition table or guard clauses;
- dead code, unused helpers, commented-out implementations, fake TODOs, or placeholder functions;
- caching without a measured need;
- premature optimization that makes the frame path hard to read;
- dependence on globally installed packages;
- a second OpenCV distribution in the same virtual environment;
- application-owned threads, `asyncio`, multiprocessing, queues, or locks;
- runtime model downloads, analytics, telemetry, or network calls.

---

## 13. Anti-overengineering and anti-AI-slop rules

The repository must look like a deliberate human-built engineering prototype, not an enterprise template or generated showcase.

### 13.1 Forbidden overengineering

- No Clean/Hexagonal/Onion architecture layers.
- No dependency-injection container or service locator.
- No event bus, command bus, plugin system, hooks framework, or generic pipeline engine.
- No abstract base class unless there are at least two required implementations in the MVP.
- No generic renderer/effect registry for only Blur and Cube.
- No serialization schema, database, API server, Docker setup, CI deployment pipeline, installer, or packaging executable.
- No feature flags, environment-variable matrix, logging framework, or configuration loader.
- No custom exception hierarchy. Use a small number of meaningful built-in exceptions and user-facing startup messages.
- No benchmark framework; a simple rolling measurement and documented manual protocol are sufficient.
- No speculative support for multiple cameras, hands, windows, platforms, or effect collections.

### 13.2 Forbidden AI slop

- No names such as `UltimateGestureManager`, `AdvancedVisionEngine`, `BaseProcessor`, or `GenericEffectHandler`.
- No marketing copy such as “revolutionary,” “seamless,” “next-generation,” or “unlock the future.”
- No README badges, roadmap theater, fake screenshots, fabricated benchmarks, or claims not measured on the target machine.
- No comments that merely restate the following line, such as `# Initialize camera manager`.
- No docstrings on trivial private helpers solely to inflate documentation.
- No decorative emoji in logs or source comments.
- No sample data, helper, option, abstraction, or configuration setting that is not exercised by the MVP.
- No “bonus” gestures or effects after acceptance criteria are met.
- No copying large tutorial code blocks without adapting ownership, lifecycle, coordinate conventions, and tests.

### 13.3 Stop rule

Implementation stops when Definition of Done and acceptance criteria pass. Any improvement not required to pass them belongs in a short “Possible future work” list in `README.md`, not in code.

---

## 14. Performance and reliability targets

### 14.1 Target environment

- Windows 10 or 11, 64-bit
- Python 3.12.x
- Integrated or USB webcam
- CPU-only inference
- One hand approximately 0.5–2.0 m from camera under ordinary indoor lighting
- Target capture request: 1280 × 720 at 30 FPS

Actual camera resolution/FPS may differ. Read the actual frame dimensions and never assume the request was honored.

### 14.2 Measurable targets

| Metric | Acceptance target | Measurement protocol |
|---|---|---|
| Display throughput | Median >= 24 FPS over a continuous 60-second run at actual 1280 × 720 on the target machine; preferred 30 FPS | Ignore first 5 seconds of warm-up; record rolling FPS samples; report median in manual test notes. |
| Gesture response | Stable gesture changes within 150 ms under a steady pose at >= 24 processed observations/s | Derived from debounce budget and verified manually for each gesture. |
| Cursor behavior | No visible one-frame jumps to `(0,0)` and materially less jitter than raw index position | Compare debug/raw point and smoothed cursor during manual calibration; debug overlay need not remain in final UI. |
| Startup | Window or actionable startup error within 5 seconds after command | Manual stopwatch is sufficient. |
| Camera read failure | One failed frame does not crash; 30 consecutive failures exit with a clear message | Automated camera wrapper test plus manual smoke test. |
| Hand loss | No accidental effect commit after hand disappears during selection/drag | State-machine tests and manual occlusion test. |
| Stability | No unhandled exception during a 10-minute normal-use session | Manual test with all required interactions. |
| Shutdown | Camera is reusable immediately after `Q`, idle `Esc`, or window close | Reopen Windows Camera or relaunch GestureCam. |

### 14.3 Performance rules

- Process one hand only.
- Use MediaPipe `VIDEO` mode with synchronous calls.
- Avoid repeated full-frame `.copy()` operations. A single output copy is acceptable if it makes inference input and rendering ownership clear.
- Blur only the selected ROI, never the entire frame and crop afterward.
- Do not allocate history larger than needed for gesture debounce and rolling FPS.
- Do not resize the frame multiple times per iteration.
- Do not add threading before profiling proves the synchronous pipeline cannot reach the target. Threading remains outside this MVP even if the preferred 30 FPS is not reached; first reduce redundant work and document hardware limits.

---

## 15. Environment setup and runbook

### 15.1 Manual prerequisites

The user is responsible only for:

1. Installing Python 3.12 alongside any other Python version.
2. Confirming the webcam works in the Windows Camera application.
3. Granting Windows camera permission to desktop applications.
4. Providing the project directory and internet access during initial dependency/model setup.

Do not uninstall Python 3.14 or install project packages globally.

### 15.2 Required PowerShell setup

From the repository root:

```powershell
py --list
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
New-Item -ItemType Directory -Force assets | Out-Null
Invoke-WebRequest `
  -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" `
  -OutFile "assets\hand_landmarker.task"
& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\python.exe -m gesturecam
```

Activation is optional; commands using the virtual environment's interpreter must work even if PowerShell execution policy blocks `Activate.ps1`.

If activation is desired:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
python -m gesturecam
```

`python --version` must report Python 3.12.x inside the environment.

### 15.3 Startup errors

Provide concise actionable messages for:

- wrong Python major/minor;
- missing or empty model asset;
- camera cannot be opened;
- frame stream fails repeatedly;
- MediaPipe initialization failure.

Messages name the failing resource and the next action. They must not expose a stack trace during ordinary setup failures unless a debug environment is explicitly added later; unexpected programmer errors may retain a traceback.

---

## 16. Testing strategy

### 16.1 Test boundaries

Tests must focus on deterministic core logic. Do not mock OpenCV or MediaPipe internals extensively. Instead, keep their adapters thin and test project-owned behavior with synthetic landmarks, generated NumPy frames, and fake camera results.

### 16.2 Required automated tests

#### Geometry

- Euclidean distance and angle for known points.
- Angle handles zero-length vectors without NaN propagation or crash.
- Rectangle normalization works for all four drag directions.
- Normalized-to-pixel conversion clamps negative, `1.0`, and out-of-range inputs.
- Rectangle hit testing includes intended boundaries.
- Rectangle translation/clamping keeps cube wireframe visible.

#### Gesture features and classification

- Synthetic canonical fixtures classify Open Palm, Fist, Pointing, and Pinch.
- A non-matching/ambiguous pose returns Unknown.
- Pinch start threshold, hysteresis band, and release threshold behave exactly as specified.
- Pinch has priority over finger-pose gestures.
- Fist and Pointing ignore thumb only where specified.
- Scale-equivalent synthetic hands produce the same gesture.
- Invalid or missing landmarks return Unknown rather than raising.

Fixtures may be small landmark builders in `tests/`; do not check in photos of people or video recordings.

#### Temporal behavior

- One noisy frame does not change the stable gesture.
- Three consecutive observations emit exactly one `entered` event.
- Holding a gesture does not emit repeated `entered` events.
- Three valid release observations emit exactly one Pinch `released` event.
- Cursor EMA initializes at the first point and resets after prolonged hand loss.

#### Interaction state machine

- Each row of the transition table has a test.
- Valid selection commits; undersized selection does not replace the prior effect.
- New selection replaces only the current mode's prior effect.
- Mode changes during active interaction are ignored.
- Fist cancels active selection and restores active cube drag.
- Idle fist deletes once per entry, not every held frame.
- Hand return inside grace resumes; grace expiry cancels/rolls back.
- Cube grabbing preserves offset and release commits position.
- `Q` requests shutdown from every state.

#### Effects

- Blur changes pixels only inside a valid ROI.
- Empty/clamped-invalid ROI leaves the frame unchanged without crashing.
- Cube depth respects min/max bounds.
- Cube drawing and selection preview accept rectangles touching frame boundaries.

#### Resource behavior

- Fake camera open failure returns the expected user-facing failure.
- One failed read is tolerated.
- Thirty consecutive failed reads request controlled shutdown.
- Cleanup is called when the main loop exits normally and when a controlled exception occurs.

### 16.3 Manual hardware test matrix

Automated tests cannot validate physical gesture comfort. Complete and record this checklist in `README.md` or a short `MANUAL_TESTS.md` only if keeping the README readable requires it:

| Scenario | Expected result |
|---|---|
| Camera permission denied/unavailable | Actionable error; no hanging empty window. |
| Open palm, fist, pointing, pinch held for 2 seconds each | Correct label is stable for the majority of the hold; no rapid flicker. |
| Pinch near threshold | Hysteresis prevents rapid select/release. |
| Blur drag in four directions | Preview follows cursor and final ROI is normalized. |
| Release a 10 × 10 selection | Preview disappears; prior effect remains unchanged. |
| Create second blur | It replaces the first; it does not add another. |
| Create cube then pinch inside it | Cube moves without snapping. |
| Pinch outside cube in Cube mode | Starts a new cube selection. |
| Fist during selection | Cancels without committing. |
| Fist while idle | Deletes current mode's effect once. |
| Hide hand during selection for >250 ms | Selection cancels; no accidental commit. |
| Switch B/C | Mode changes only while idle; effects in the other mode remain. |
| Low light and busy background | Degradation is understandable and does not crash. |
| 60-second performance run | Median FPS target is measured after warm-up. |
| 10-minute mixed-use run | No unhandled exception or camera leak. |
| Exit and relaunch | Camera is available immediately. |

Record actual hardware, actual camera resolution, median FPS, date, and any threshold adjustment. Do not fabricate results when no webcam test was performed.

### 16.4 Test commands

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m compileall gesturecam tests
```

All automated tests must pass from a clean virtual environment. No automated test may require network, webcam, display window, or a person.

---

## 17. Milestones and implementation order

Each milestone ends with passing existing tests and a small runnable result. Do not scaffold every future module with placeholders on day one.

### M0 — Environment and dependency proof

Deliver:

- required files for virtual-environment setup;
- exact dependency pins;
- model download instructions;
- import/Hand Landmarker smoke proof on Python 3.12.

Exit criteria:

- clean environment installs successfully;
- model initializes and closes;
- no duplicate OpenCV distribution is installed.

### M1 — Camera lifecycle

Deliver:

- mirrored camera window;
- actual frame-size handling;
- rolling FPS;
- controlled read failures and clean exit.

Exit criteria:

- camera runs for 60 seconds and is released on exit.

### M2 — Hand tracking and overlay

Deliver:

- one-hand MediaPipe adapter using `VIDEO` timestamps;
- landmark/connection drawing;
- hand present/absent status.

Exit criteria:

- 21 landmarks follow one visible hand; temporary absence does not crash.

### M3 — Deterministic gestures and cursor

Deliver:

- pure geometry and finger features;
- raw classifier and priority;
- pinch hysteresis and temporal events;
- EMA cursor;
- unit tests for all rules.

Exit criteria:

- four gestures and Unknown are visibly labeled and automated tests pass.

### M4 — State machine and Blur mode

Deliver:

- explicit modes/states/transitions;
- selection preview and minimum size;
- persistent single ROI blur;
- fist/hand-loss cancellation;
- state and effect tests.

Exit criteria:

- pinch-drag-release reliably creates/replaces blur; invalid selection never overwrites a valid one.

### M5 — Cube mode and manipulation

Deliver:

- pseudo-3D cube rendering;
- creation from selection;
- hit test, grab offset, movement, clamp, commit/rollback;
- deletion and tests.

Exit criteria:

- cube can be created, moved without snapping, replaced, canceled, and deleted.

### M6 — Hardening and handoff

Deliver:

- all startup errors and cleanup paths;
- README setup/run/test/troubleshooting/calibration notes;
- completed automated suite;
- completed manual matrix where hardware is available;
- complexity and dead-code review.

Exit criteria:

- Definition of Done and all automated acceptance criteria pass; manual items are truthfully marked pass/fail/not run.

---

## 18. Risks and mitigations

| Risk | Impact | MVP mitigation | Not allowed as first response |
|---|---|---|---|
| MediaPipe/OpenCV/NumPy binary incompatibility | Setup failure | Exact compatible pins; smoke test first; one OpenCV distribution only. | Installing packages globally or mixing OpenCV wheels. |
| MediaPipe model asset missing | Tracker cannot start | Explicit asset path validation and one documented download command. | Silent runtime download or unexplained crash. |
| Gesture flicker | Accidental actions | Scale-normalized rules, pinch hysteresis, three-observation debounce. | Adding a custom ML classifier. |
| Cursor jitter | Uncomfortable dragging | EMA with named alpha; reset after hand loss. | Complex filters or prediction before measuring EMA. |
| Hand temporarily disappears | Accidental commit/jump | 250 ms grace, then cancel/rollback. | Committing on loss. |
| Camera ignores 720p request | Wrong coordinates/targets | Use actual frame shape for all pixel conversion. | Hard-coded 1280 × 720 math. |
| Low FPS | Interaction lag | One hand, synchronous video mode, ROI-only blur, no redundant copies. | Threading, multiprocessing, GPU stack, or resolution cascade without profiling. |
| Mirroring mismatch | Cursor moves opposite hand | Mirror before detection and use one coordinate convention. | Flipping only the display after inference. |
| Fist held deletes repeatedly | Effects disappear unexpectedly | Edge-triggered `entered` event. | Time sleeps or arbitrary global cooldowns. |
| Cube jumps on grab | Poor interaction | Preserve cursor-to-object grab offset. | Snapping to cursor. |
| Broad exception handling masks bugs | Unreliable prototype | Catch only expected resource failures; `finally` for cleanup. | `except Exception: pass`. |
| Scope expansion | Delay and complexity | Complexity budget, non-goals, stop rule. | “Bonus” features. |

---

## 19. Non-goals

The MVP explicitly does not include:

- two-hand interaction, resizing, rotation, swipe, or wrist-rotation controls;
- more than four recognized gestures;
- gesture customization or calibration UI;
- custom gesture ML, training, datasets, or learned classifiers;
- true 3D, OpenGL, ModernGL, PyOpenGL, Pygame, physics, lighting, or depth occlusion;
- PySide6/Qt, Tkinter, web UI, mobile UI, or browser deployment;
- camera recording, screenshots, export, persistence, undo history, project files, or settings storage;
- multiple cameras, camera picker, resolution picker, or hot-plug recovery;
- multiple concurrent hands, users, blur regions, or cubes;
- face/body tracking, background segmentation, AR anchors, or spatial mapping;
- login, database, API, cloud sync, telemetry, analytics, crash reporting, or network features;
- plugin architecture, scripting interface, extension SDK, or reusable framework;
- installer, executable bundling, auto-update, signing, deployment, Docker, or cloud hosting;
- GPU/CUDA acceleration or performance work beyond the stated CPU targets;
- accessibility certification, production security audit, localization, or commercial distribution.

---

## 20. Acceptance criteria

### 20.1 Automated acceptance

The coding agent may mark an item complete only with a passing test or direct deterministic check.

- [ ] AC-A01: A clean Python 3.12 virtual environment installs exact direct dependencies from `requirements-dev.txt`.
- [ ] AC-A02: The environment contains only one OpenCV wheel distribution and `import cv2` succeeds.
- [ ] AC-A03: Missing/empty model asset produces an actionable controlled startup failure.
- [ ] AC-A04: Geometry tests cover distances, angles, all drag directions, clamping, and hit testing.
- [ ] AC-A05: Synthetic fixtures classify all four gestures and Unknown according to the exact priority rules.
- [ ] AC-A06: Pinch thresholds demonstrate enter, hysteresis preservation, and release.
- [ ] AC-A07: Three-observation debounce and three-observation pinch release emit one-shot events correctly.
- [ ] AC-A08: Cursor EMA initializes without origin jump and resets after prolonged loss.
- [ ] AC-A09: Every interaction transition in Section 9.3 has an automated test.
- [ ] AC-A10: A valid selection commits and an invalid selection cannot replace a prior effect.
- [ ] AC-A11: Blur modifies only the normalized/clamped ROI.
- [ ] AC-A12: Cube depth, drawing bounds, grab offset, movement, commit, and rollback are tested.
- [ ] AC-A13: Holding a fist cannot repeat deletion.
- [ ] AC-A14: Hand-loss expiry cancels selection and rolls back cube movement without committing.
- [ ] AC-A15: Camera read failures and cleanup paths are tested with a fake adapter.
- [ ] AC-A16: `python -m pytest -q` passes without camera, window, network, or human input.
- [ ] AC-A17: `python -m compileall gesturecam tests` succeeds.
- [ ] AC-A18: Source structure and dependencies remain within the hard complexity budget.

### 20.2 Manual hardware acceptance

These require a real webcam and must never be claimed without execution.

- [ ] AC-M01: `python -m gesturecam` opens the default camera in <=5 seconds or shows an actionable error.
- [ ] AC-M02: The displayed feed is mirrored and the cursor moves in the same apparent direction as the hand.
- [ ] AC-M03: One hand produces 21 visibly aligned landmarks and a correct hand-present status.
- [ ] AC-M04: Open Palm, Fist, Pointing, and Pinch each become stable within 150 ms under a steady pose at target FPS.
- [ ] AC-M05: Pointing cursor motion is visibly smoother than raw landmark jitter and never jumps to the origin.
- [ ] AC-M06: In Blur mode, pinch-drag-release in all four directions creates the intended blur rectangle.
- [ ] AC-M07: A selection under 30 × 30 pixels is discarded without replacing the prior blur/cube.
- [ ] AC-M08: In Cube mode, pinch-drag-release creates a bounded pseudo-3D cube.
- [ ] AC-M09: Pinching inside the cube moves it without snapping; release commits its location.
- [ ] AC-M10: Pinching outside the cube begins a replacement cube selection.
- [ ] AC-M11: Fist cancels active manipulation; while idle it deletes the current mode's effect exactly once.
- [ ] AC-M12: Hand loss longer than 250 ms during manipulation causes cancel/rollback and no accidental commit.
- [ ] AC-M13: `B`/`C` switch mode only while idle; both modes' committed effects may remain visible.
- [ ] AC-M14: Median displayed FPS is >=24 during the defined 60-second 720p protocol on the target machine, or the actual camera mode and measured hardware limitation are documented as a failed criterion.
- [ ] AC-M15: A 10-minute mixed-use session completes without unhandled exception or unreleased camera.
- [ ] AC-M16: `Q`, idle `Esc`, and normal window close release the webcam for immediate relaunch.

### 20.3 Documentation acceptance

- [ ] AC-D01: README contains exact Windows setup, model download, run, test, controls, and troubleshooting commands.
- [ ] AC-D02: README states Python 3.12 and warns against global installs and multiple OpenCV distributions.
- [ ] AC-D03: README explains the mirrored coordinate convention, one-hand/one-effect limits, and pseudo-3D cube limitation.
- [ ] AC-D04: Any dependency-pin or threshold change includes the observed problem, new value/version, and verification result.
- [ ] AC-D05: Manual results list hardware, actual resolution, median FPS, date, and honest pass/fail/not-run status.
- [ ] AC-D06: README is concise engineering documentation without marketing copy, badges, fake metrics, or speculative architecture.

---

## 21. Definition of Done

The GestureCam MVP is done only when all of the following are true:

1. All automated acceptance criteria pass in a clean Python 3.12 virtual environment.
2. Required source code, tests, model setup instructions, and README exist in the specified simple structure.
3. Required gestures, state transitions, Blur mode, Cube mode, cancellation, deletion, and cleanup are implemented exactly as specified.
4. The code remains within the hard complexity budget and contains none of the rejected smells or forbidden architecture.
5. The coding agent has performed and truthfully recorded manual hardware checks where a webcam is available. Hardware-only criteria that could not be run are explicitly marked `NOT RUN`; they are not silently treated as passing.
6. There are no unhandled known normal-use failures, dead code, placeholder implementations, fake TODOs, commented-out alternatives, unused dependencies, or per-frame console spam.
7. The application starts with `python -m gesturecam`, exits cleanly, and the camera can be reopened immediately.
8. No non-goal or bonus feature has been implemented.

When these conditions are met, stop. Do not add polish or extensibility beyond the document.

---

## 22. Coding-agent execution constraints

The implementing agent must:

1. Work milestone by milestone in the documented order.
2. Inspect the current repository before editing and preserve unrelated user work.
3. Establish the clean Python 3.12 environment and dependency smoke test before feature implementation.
4. Add tests alongside pure logic and run the relevant subset after each meaningful change.
5. Run the full test and compile commands before handoff.
6. Keep hardware adapters thin and core logic deterministic.
7. Prefer root-cause fixes over thresholds or sleeps that mask behavior.
8. Avoid changing architecture or pins without an observed failure and written reason.
9. Report which manual hardware checks were actually executed.
10. Stop when Definition of Done is met.

The agent must not claim gesture accuracy, FPS, stability duration, or hardware compatibility without measuring it.

---

## 23. Implementation references

These references support the prescribed APIs and setup. This PRD remains the product-behavior source of truth.

- [MediaPipe Hand Landmarker Python API](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/HandLandmarker)
- [MediaPipe Hand Landmarker options](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/HandLandmarkerOptions)
- [MediaPipe Hand Landmarker result](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/HandLandmarkerResult)
- [OpenCV Python video capture tutorial](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html)
- [OpenCV Python package installation notes](https://pypi.org/project/opencv-python/)
- [MediaPipe package metadata](https://pypi.org/project/mediapipe/0.10.35/)
- [NumPy 2.2.6 package metadata](https://pypi.org/project/numpy/2.2.6/)
- [pytest package metadata](https://pypi.org/project/pytest/9.1.1/)
