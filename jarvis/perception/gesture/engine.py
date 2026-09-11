"""Gesture Perception Engine matching 04_GESTURE_ENGINE.md."""

from collections import deque
import threading
import time
from typing import Callable, Deque, List, Optional, Tuple
import numpy as np

from jarvis.core.config import JarvisConfig
from jarvis.core.logging import AuditLogger
from jarvis.perception.gesture.camera import CameraInterface, MockCamera, OpenCVCamera
from jarvis.perception.gesture.classifier import GestureClassifier
from jarvis.perception.gesture.landmarker import LandmarkerInterface, MediaPipeLandmarker, MockLandmarker
from jarvis.perception.gesture.models import (
    GestureEvent,
    GestureType,
    HandLandmarks,
    LandmarkIndex,
    LandmarkPoint,
)
from jarvis.router.router import InputEvent


class GestureEngine:
    """End-to-end gesture perception engine enforcing privacy, confidence, and cooldown contracts."""

    def __init__(
        self,
        config: Optional[JarvisConfig] = None,
        camera: Optional[CameraInterface] = None,
        landmarker: Optional[LandmarkerInterface] = None,
        classifier: Optional[GestureClassifier] = None,
        logger: Optional[AuditLogger] = None,
    ):
        self.config = config or JarvisConfig()
        self.logger = logger
        self.classifier = classifier or GestureClassifier()
        self.camera = camera
        self.landmarker = landmarker

        self._last_gesture_time_ms: int = 0
        self._last_gesture_name: Optional[str] = None
        self._active_gesture_start_ms: Optional[int] = None
        self._wrist_history: Deque[Tuple[int, LandmarkPoint]] = deque(maxlen=15)
        self._camera_indicator_callback: Optional[Callable[[bool], None]] = None

    @property
    def is_camera_active(self) -> bool:
        """Check whether camera is currently active (for UI/HUD indicator)."""
        return self.camera is not None and self.camera.is_active

    def set_camera_indicator_callback(self, callback: Callable[[bool], None]) -> None:
        """Register a callback for UI/HUD camera indicator updates."""
        self._camera_indicator_callback = callback

    def start(self) -> bool:
        """Start the gesture engine if and only if vision is explicitly enabled (opt-in)."""
        # Privacy check per 04_GESTURE_ENGINE.md
        if not self.config.vision.enabled:
            return False

        if self.camera is None:
            self.camera = OpenCVCamera(camera_index=self.config.vision.camera_index)
        if self.landmarker is None:
            self.landmarker = MediaPipeLandmarker()

        started = self.camera.start()
        if started and self._camera_indicator_callback:
            self._camera_indicator_callback(True)
        return started

    def stop(self) -> None:
        """Stop camera capture and update active indicator."""
        if self.camera is not None:
            self.camera.stop()
        if self._camera_indicator_callback:
            self._camera_indicator_callback(False)

    def process_landmarks(
        self,
        landmarks: HandLandmarks,
        current_time_ms: Optional[int] = None,
    ) -> Optional[GestureEvent]:
        """Process a detected hand landmark set through classifier, confidence filter, and cooldown."""
        now = current_time_ms if current_time_ms is not None else int(time.time() * 1000)

        # 0. Check landmark detection confidence per 04_GESTURE_ENGINE.md
        if landmarks.confidence < self.config.vision.gesture_confidence:
            return None

        # 1. Update wrist trajectory history for swipe motion
        wrist = landmarks.get(LandmarkIndex.WRIST)
        self._wrist_history.append((now, wrist))

        # 2. Check dynamic motion gestures (Swipe Left / Swipe Right)
        motion_result = self.classifier.classify_motion(list(self._wrist_history))
        gesture_type = None
        confidence = 0.0

        if motion_result is not None:
            gesture_type, confidence = motion_result
            self._wrist_history.clear()
        else:
            # 3. Static gesture classification
            gesture_type, confidence = self.classifier.classify_static(landmarks)

        if gesture_type is None:
            self._active_gesture_start_ms = None
            return None

        # 4. Confidence threshold check per 04_GESTURE_ENGINE.md
        effective_confidence = min(landmarks.confidence, confidence)
        if effective_confidence < self.config.vision.gesture_confidence:
            return None

        gesture_name = gesture_type.value

        # 5. Cooldown / Debounce check
        time_since_last = now - self._last_gesture_time_ms
        if time_since_last < self.config.vision.cooldown_ms:
            # Special case: Open palm STOP_OR_PAUSE or fist STOP always overrides
            if gesture_type not in {GestureType.STOP_OR_PAUSE, GestureType.STOP}:
                return None

        # Calculate duration
        if self._last_gesture_name == gesture_name and self._active_gesture_start_ms is not None:
            duration = now - self._active_gesture_start_ms
        else:
            self._active_gesture_start_ms = now
            duration = 50

        self._last_gesture_time_ms = now
        self._last_gesture_name = gesture_name

        return GestureEvent(
            type="gesture",
            name=gesture_name,
            confidence=effective_confidence,
            hand=landmarks.handedness,
            timestamp=now,
            duration_ms=duration,
        )

    def process_frame(self, frame: np.ndarray, current_time_ms: Optional[int] = None) -> Optional[GestureEvent]:
        """Run landmark detection on frame and classify into gesture."""
        if not self.config.vision.enabled:
            return None

        if self.landmarker is None:
            self.landmarker = MediaPipeLandmarker()

        landmarks = self.landmarker.detect(frame)
        if landmarks is None:
            return None

        return self.process_landmarks(landmarks, current_time_ms=current_time_ms)

    def to_input_event(self, gesture_event: GestureEvent, event_id: Optional[str] = None) -> InputEvent:
        """Convert a GestureEvent into a router InputEvent."""
        eid = event_id or f"g-{hex(gesture_event.timestamp)[-4:]}"
        return InputEvent(
            event_id=eid,
            channel="gesture",
            raw_payload=gesture_event.name,
            confidence=gesture_event.confidence,
            timestamp_ms=gesture_event.timestamp,
        )
