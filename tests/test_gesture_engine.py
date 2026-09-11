"""Tests for Gesture Engine matching 04_GESTURE_ENGINE.md."""

import pytest
from jarvis.core.config import JarvisConfig, VisionSection
from jarvis.execution.actions.input import VirtualInputBackend
from jarvis.perception.gesture.camera import MockCamera
from jarvis.perception.gesture.classifier import GestureClassifier
from jarvis.perception.gesture.engine import GestureEngine
from jarvis.perception.gesture.landmarker import MockLandmarker
from jarvis.perception.gesture.models import (
    GestureEvent,
    GestureType,
    HandLandmarks,
    LandmarkIndex,
    LandmarkPoint,
)
from jarvis.pipeline import ExecutionPipeline


def create_blank_landmarks() -> list[LandmarkPoint]:
    """Create 21 neutral points centered at wrist (0.5, 0.7)."""
    return [LandmarkPoint(x=0.5, y=0.7, z=0.0) for _ in range(21)]


def make_open_palm_landmarks() -> HandLandmarks:
    """All 5 fingers extended upward away from wrist."""
    pts = create_blank_landmarks()
    # Wrist at (0.5, 0.8)
    pts[LandmarkIndex.WRIST] = LandmarkPoint(x=0.5, y=0.8, z=0.0)
    # Thumb extended outward to the left
    pts[LandmarkIndex.THUMB_CMC] = LandmarkPoint(x=0.45, y=0.75, z=0.0)
    pts[LandmarkIndex.THUMB_MCP] = LandmarkPoint(x=0.40, y=0.70, z=0.0)
    pts[LandmarkIndex.THUMB_IP] = LandmarkPoint(x=0.35, y=0.65, z=0.0)
    pts[LandmarkIndex.THUMB_TIP] = LandmarkPoint(x=0.30, y=0.60, z=0.0)
    # Index extended upward
    pts[LandmarkIndex.INDEX_FINGER_MCP] = LandmarkPoint(x=0.45, y=0.60, z=0.0)
    pts[LandmarkIndex.INDEX_FINGER_PIP] = LandmarkPoint(x=0.45, y=0.50, z=0.0)
    pts[LandmarkIndex.INDEX_FINGER_DIP] = LandmarkPoint(x=0.45, y=0.40, z=0.0)
    pts[LandmarkIndex.INDEX_FINGER_TIP] = LandmarkPoint(x=0.45, y=0.30, z=0.0)
    # Middle extended upward
    pts[LandmarkIndex.MIDDLE_FINGER_MCP] = LandmarkPoint(x=0.50, y=0.60, z=0.0)
    pts[LandmarkIndex.MIDDLE_FINGER_PIP] = LandmarkPoint(x=0.50, y=0.48, z=0.0)
    pts[LandmarkIndex.MIDDLE_FINGER_DIP] = LandmarkPoint(x=0.50, y=0.38, z=0.0)
    pts[LandmarkIndex.MIDDLE_FINGER_TIP] = LandmarkPoint(x=0.50, y=0.28, z=0.0)
    # Ring extended upward
    pts[LandmarkIndex.RING_FINGER_MCP] = LandmarkPoint(x=0.55, y=0.60, z=0.0)
    pts[LandmarkIndex.RING_FINGER_PIP] = LandmarkPoint(x=0.55, y=0.50, z=0.0)
    pts[LandmarkIndex.RING_FINGER_DIP] = LandmarkPoint(x=0.55, y=0.42, z=0.0)
    pts[LandmarkIndex.RING_FINGER_TIP] = LandmarkPoint(x=0.55, y=0.32, z=0.0)
    # Pinky extended upward
    pts[LandmarkIndex.PINKY_MCP] = LandmarkPoint(x=0.60, y=0.62, z=0.0)
    pts[LandmarkIndex.PINKY_PIP] = LandmarkPoint(x=0.60, y=0.54, z=0.0)
    pts[LandmarkIndex.PINKY_DIP] = LandmarkPoint(x=0.60, y=0.46, z=0.0)
    pts[LandmarkIndex.PINKY_TIP] = LandmarkPoint(x=0.60, y=0.38, z=0.0)
    return HandLandmarks(landmarks=pts, handedness="right", confidence=0.96)


def make_fist_landmarks() -> HandLandmarks:
    """All 5 fingers curled towards wrist."""
    pts = create_blank_landmarks()
    pts[LandmarkIndex.WRIST] = LandmarkPoint(x=0.5, y=0.8, z=0.0)
    # Thumb curled across palm
    pts[LandmarkIndex.INDEX_FINGER_MCP] = LandmarkPoint(x=0.45, y=0.65, z=0.0)
    pts[LandmarkIndex.THUMB_MCP] = LandmarkPoint(x=0.45, y=0.70, z=0.0)
    pts[LandmarkIndex.THUMB_IP] = LandmarkPoint(x=0.46, y=0.68, z=0.0)
    pts[LandmarkIndex.THUMB_TIP] = LandmarkPoint(x=0.46, y=0.67, z=0.0)  # near index MCP
    # All 4 fingertips curled below their PIPs (towards wrist)
    for tip_idx, pip_idx, mcp_idx, x_pos in [
        (LandmarkIndex.INDEX_FINGER_TIP, LandmarkIndex.INDEX_FINGER_PIP, LandmarkIndex.INDEX_FINGER_MCP, 0.45),
        (LandmarkIndex.MIDDLE_FINGER_TIP, LandmarkIndex.MIDDLE_FINGER_PIP, LandmarkIndex.MIDDLE_FINGER_MCP, 0.50),
        (LandmarkIndex.RING_FINGER_TIP, LandmarkIndex.RING_FINGER_PIP, LandmarkIndex.RING_FINGER_MCP, 0.55),
        (LandmarkIndex.PINKY_TIP, LandmarkIndex.PINKY_PIP, LandmarkIndex.PINKY_MCP, 0.60),
    ]:
        pts[mcp_idx] = LandmarkPoint(x=x_pos, y=0.60, z=0.0)
        pts[pip_idx] = LandmarkPoint(x=x_pos, y=0.55, z=0.0)
        pts[tip_idx] = LandmarkPoint(x=x_pos, y=0.68, z=0.0)  # curled down
    return HandLandmarks(landmarks=pts, handedness="right", confidence=0.95)


def make_pinch_landmarks() -> HandLandmarks:
    """Thumb tip and Index tip touching (distance < 0.05)."""
    pts = make_open_palm_landmarks().landmarks
    # Bring thumb tip and index tip together at (0.42, 0.45)
    pts[LandmarkIndex.INDEX_FINGER_TIP] = LandmarkPoint(x=0.42, y=0.45, z=0.0)
    pts[LandmarkIndex.THUMB_TIP] = LandmarkPoint(x=0.43, y=0.46, z=0.0)
    return HandLandmarks(landmarks=pts, handedness="right", confidence=0.97)


def make_index_point_landmarks() -> HandLandmarks:
    """Index finger extended; middle, ring, pinky, thumb curled."""
    hand = make_fist_landmarks()
    pts = hand.landmarks
    # Extend index finger upward
    pts[LandmarkIndex.INDEX_FINGER_PIP] = LandmarkPoint(x=0.45, y=0.50, z=0.0)
    pts[LandmarkIndex.INDEX_FINGER_TIP] = LandmarkPoint(x=0.45, y=0.30, z=0.0)
    return HandLandmarks(landmarks=pts, handedness="right", confidence=0.95)


def make_two_fingers_landmarks() -> HandLandmarks:
    """Index and middle extended upward; ring, pinky, thumb curled."""
    hand = make_fist_landmarks()
    pts = hand.landmarks
    pts[LandmarkIndex.INDEX_FINGER_PIP] = LandmarkPoint(x=0.45, y=0.50, z=0.0)
    pts[LandmarkIndex.INDEX_FINGER_TIP] = LandmarkPoint(x=0.45, y=0.30, z=0.0)
    pts[LandmarkIndex.MIDDLE_FINGER_PIP] = LandmarkPoint(x=0.50, y=0.48, z=0.0)
    pts[LandmarkIndex.MIDDLE_FINGER_TIP] = LandmarkPoint(x=0.50, y=0.28, z=0.0)
    return HandLandmarks(landmarks=pts, handedness="right", confidence=0.94)


def make_thumbs_up_landmarks() -> HandLandmarks:
    """Thumb pointed upward (y < mcp.y - 0.05); all 4 fingers curled."""
    hand = make_fist_landmarks()
    pts = hand.landmarks
    # Extend thumb upward
    pts[LandmarkIndex.INDEX_FINGER_MCP] = LandmarkPoint(x=0.50, y=0.60, z=0.0)
    pts[LandmarkIndex.THUMB_MCP] = LandmarkPoint(x=0.40, y=0.65, z=0.0)
    pts[LandmarkIndex.THUMB_IP] = LandmarkPoint(x=0.40, y=0.55, z=0.0)
    pts[LandmarkIndex.THUMB_TIP] = LandmarkPoint(x=0.40, y=0.45, z=0.0)
    return HandLandmarks(landmarks=pts, handedness="right", confidence=0.95)


def make_thumbs_down_landmarks() -> HandLandmarks:
    """Thumb pointed downward (y > mcp.y + 0.05); all 4 fingers curled."""
    hand = make_fist_landmarks()
    pts = hand.landmarks
    pts[LandmarkIndex.INDEX_FINGER_MCP] = LandmarkPoint(x=0.50, y=0.55, z=0.0)
    pts[LandmarkIndex.THUMB_MCP] = LandmarkPoint(x=0.40, y=0.60, z=0.0)
    pts[LandmarkIndex.THUMB_IP] = LandmarkPoint(x=0.40, y=0.70, z=0.0)
    pts[LandmarkIndex.THUMB_TIP] = LandmarkPoint(x=0.40, y=0.80, z=0.0)
    return HandLandmarks(landmarks=pts, handedness="right", confidence=0.95)


def test_privacy_opt_in_default():
    """Rule 4 & 17_CONFIG_SCHEMA.md: camera stays off until explicitly enabled."""
    cfg = JarvisConfig()
    assert cfg.vision.enabled is False

    mock_cam = MockCamera()
    engine = GestureEngine(config=cfg, camera=mock_cam)

    # Calling start should refuse to start camera
    started = engine.start()
    assert started is False
    assert engine.is_camera_active is False
    assert mock_cam.is_active is False

    # Frames are rejected when disabled
    frame = mock_cam.read_frame()
    result = engine.process_frame(frame)
    assert result is None


def test_privacy_opt_in_explicit():
    """Camera starts and triggers indicator when vision.enabled = True."""
    cfg = JarvisConfig(vision=VisionSection(enabled=True))
    mock_cam = MockCamera()
    engine = GestureEngine(config=cfg, camera=mock_cam)

    indicator_states = []
    engine.set_camera_indicator_callback(lambda active: indicator_states.append(active))

    started = engine.start()
    assert started is True
    assert engine.is_camera_active is True
    assert indicator_states == [True]

    engine.stop()
    assert engine.is_camera_active is False
    assert indicator_states == [True, False]


def test_classifier_all_canonical_gestures():
    """Test geometric classification of all canonical gestures."""
    classifier = GestureClassifier()

    # 1. Open Palm -> STOP_OR_PAUSE
    g_palm, conf = classifier.classify_static(make_open_palm_landmarks())
    assert g_palm == GestureType.STOP_OR_PAUSE
    assert conf >= 0.85

    # 2. Fist -> STOP
    g_fist, conf = classifier.classify_static(make_fist_landmarks())
    assert g_fist == GestureType.STOP
    assert conf >= 0.85

    # 3. Pinch -> SELECT_OR_CLICK
    g_pinch, conf = classifier.classify_static(make_pinch_landmarks())
    assert g_pinch == GestureType.SELECT_OR_CLICK
    assert conf >= 0.85

    # 4. Index Point -> POINTER_MODE
    g_point, conf = classifier.classify_static(make_index_point_landmarks())
    assert g_point == GestureType.POINTER_MODE
    assert conf >= 0.85

    # 5. Two Fingers -> SCROLL_MODE
    g_scroll, conf = classifier.classify_static(make_two_fingers_landmarks())
    assert g_scroll == GestureType.SCROLL_MODE
    assert conf >= 0.85

    # 6. Thumbs Up -> CONFIRM
    g_confirm, conf = classifier.classify_static(make_thumbs_up_landmarks())
    assert g_confirm == GestureType.CONFIRM
    assert conf >= 0.85

    # 7. Thumbs Down -> CANCEL
    g_cancel, conf = classifier.classify_static(make_thumbs_down_landmarks())
    assert g_cancel == GestureType.CANCEL
    assert conf >= 0.85

    # 8. Dynamic Swipe Right -> NEXT
    wrist_history_right = [
        (100, LandmarkPoint(x=0.3, y=0.5)),
        (200, LandmarkPoint(x=0.5, y=0.5)),
        (300, LandmarkPoint(x=0.7, y=0.5)),
    ]
    motion_next = classifier.classify_motion(wrist_history_right)
    assert motion_next is not None
    assert motion_next[0] == GestureType.NEXT
    assert motion_next[1] >= 0.85

    # 9. Dynamic Swipe Left -> PREVIOUS
    wrist_history_left = [
        (100, LandmarkPoint(x=0.7, y=0.5)),
        (200, LandmarkPoint(x=0.5, y=0.5)),
        (300, LandmarkPoint(x=0.3, y=0.5)),
    ]
    motion_prev = classifier.classify_motion(wrist_history_left)
    assert motion_prev is not None
    assert motion_prev[0] == GestureType.PREVIOUS
    assert motion_prev[1] >= 0.85


def test_confidence_threshold_gating():
    """Per 04_GESTURE_ENGINE.md: low confidence gestures (< 0.85) are discarded."""
    cfg = JarvisConfig(vision=VisionSection(enabled=True, gesture_confidence=0.85))
    engine = GestureEngine(config=cfg)

    # Synthetic noisy/ambiguous landmarks returning low confidence
    low_conf_hand = HandLandmarks(
        landmarks=create_blank_landmarks(),
        handedness="right",
        confidence=0.60,
    )
    # Neutral/flat hand does not match any gesture schema
    res = engine.process_landmarks(low_conf_hand, current_time_ms=1000)
    assert res is None


def test_cooldown_and_emergency_override():
    """Per 04_GESTURE_ENGINE.md: cooldown suppresses rapid gestures, but STOP overrides immediately."""
    cfg = JarvisConfig(vision=VisionSection(enabled=True, cooldown_ms=500))
    engine = GestureEngine(config=cfg)

    pinch = make_pinch_landmarks()
    ev1 = engine.process_landmarks(pinch, current_time_ms=1000)
    assert ev1 is not None
    assert ev1.name == "SELECT_OR_CLICK"

    # Second pinch 100ms later (within 500ms cooldown) is suppressed
    ev2 = engine.process_landmarks(pinch, current_time_ms=1100)
    assert ev2 is None

    # But open palm STOP_OR_PAUSE at 1200ms immediately breaks through cooldown!
    palm = make_open_palm_landmarks()
    ev_stop = engine.process_landmarks(palm, current_time_ms=1200)
    assert ev_stop is not None
    assert ev_stop.name == "STOP_OR_PAUSE"

    # After 500ms elapsed (at 1750ms), normal pinch succeeds again
    ev3 = engine.process_landmarks(pinch, current_time_ms=1750)
    assert ev3 is not None
    assert ev3.name == "SELECT_OR_CLICK"


def test_gesture_pipeline_end_to_end_mouse_click():
    """End-to-end: Pinch gesture -> SELECT_OR_CLICK -> Router -> click -> VirtualInputBackend verified."""
    cfg = JarvisConfig(vision=VisionSection(enabled=True))
    input_backend = VirtualInputBackend()
    pipeline = ExecutionPipeline(config=cfg, input_backend=input_backend)

    engine = GestureEngine(config=cfg)
    pinch_hand = make_pinch_landmarks()
    gesture_ev = engine.process_landmarks(pinch_hand, current_time_ms=1000)
    assert gesture_ev is not None

    result = pipeline.process_gesture(gesture_ev)

    assert result["status"] == "success"
    assert result["verified"] is True
    assert result["error_code"] is None
    assert input_backend.click_count == 1
    assert "Mouse left clicked" in result["response_text"]


def test_gesture_pipeline_scroll():
    """End-to-end: Two fingers gesture -> SCROLL_MODE -> Router -> scroll -> verified."""
    cfg = JarvisConfig(vision=VisionSection(enabled=True))
    input_backend = VirtualInputBackend()
    pipeline = ExecutionPipeline(config=cfg, input_backend=input_backend)

    engine = GestureEngine(config=cfg)
    scroll_hand = make_two_fingers_landmarks()
    gesture_ev = engine.process_landmarks(scroll_hand, current_time_ms=2000)
    assert gesture_ev is not None

    result = pipeline.process_gesture(gesture_ev)

    assert result["status"] == "success"
    assert result["verified"] is True
    assert input_backend.scroll_delta == 1
