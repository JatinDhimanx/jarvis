"""Hand landmark detection abstraction matching 04_GESTURE_ENGINE.md."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
import numpy as np

from jarvis.perception.gesture.models import HandLandmarks, LandmarkPoint


class LandmarkerInterface(ABC):
    """Abstract interface for extracting 21 hand landmarks from an image frame."""

    @abstractmethod
    def detect(self, frame: np.ndarray) -> Optional[HandLandmarks]:
        """Process an RGB/BGR image frame and return detected landmarks, or None."""
        pass


class MediaPipeLandmarker(LandmarkerInterface):
    """MediaPipe Hands solution implementation."""

    def __init__(self, min_detection_confidence: float = 0.7, min_tracking_confidence: float = 0.5):
        self._hands = None
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

    def _ensure_initialized(self):
        if self._hands is None:
            import mediapipe as mp
            # Handle both classic solutions and modern mediapipe structure
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
                self._hands = mp.solutions.hands.Hands(
                    static_image_mode=False,
                    max_num_hands=1,
                    min_detection_confidence=self.min_detection_confidence,
                    min_tracking_confidence=self.min_tracking_confidence,
                )

    def detect(self, frame: np.ndarray) -> Optional[HandLandmarks]:
        try:
            self._ensure_initialized()
            if self._hands is None:
                return None

            import cv2
            # MediaPipe expects RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._hands.process(rgb_frame)

            if not results.multi_hand_landmarks:
                return None

            hand_landmarks_proto = results.multi_hand_landmarks[0]
            points = [
                LandmarkPoint(x=lm.x, y=lm.y, z=lm.z)
                for lm in hand_landmarks_proto.landmark
            ]

            handedness = "right"
            if results.multi_handedness and len(results.multi_handedness) > 0:
                handedness = results.multi_handedness[0].classification[0].label.lower()

            return HandLandmarks(landmarks=points, handedness=handedness, confidence=0.95)
        except Exception:
            return None


class MockLandmarker(LandmarkerInterface):
    """Mock landmarker for testing with synthetic landmarks."""

    def __init__(self, next_landmarks: Optional[HandLandmarks] = None):
        self.next_landmarks = next_landmarks

    def set_landmarks(self, landmarks: Optional[HandLandmarks]) -> None:
        self.next_landmarks = landmarks

    def detect(self, frame: np.ndarray) -> Optional[HandLandmarks]:
        return self.next_landmarks
