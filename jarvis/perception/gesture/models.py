"""Data structures and schemas for hand landmarks and gestures matching 04_GESTURE_ENGINE.md."""

from enum import Enum
from typing import Dict, List, Optional
import time
from pydantic import BaseModel, Field


class LandmarkIndex(int, Enum):
    """Standard 21 3D hand landmark indices (MediaPipe Hand format)."""
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_FINGER_MCP = 5
    INDEX_FINGER_PIP = 6
    INDEX_FINGER_DIP = 7
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_MCP = 9
    MIDDLE_FINGER_PIP = 10
    MIDDLE_FINGER_DIP = 11
    MIDDLE_FINGER_TIP = 12
    RING_FINGER_MCP = 13
    RING_FINGER_PIP = 14
    RING_FINGER_DIP = 15
    RING_FINGER_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


class LandmarkPoint(BaseModel):
    """Single 3D coordinate point normalized [0.0, 1.0]."""
    x: float
    y: float
    z: float = 0.0


class HandLandmarks(BaseModel):
    """Collection of 21 landmark points representing one hand."""
    landmarks: List[LandmarkPoint]
    handedness: str = "right"  # "left" | "right"
    confidence: float = 1.0

    def get(self, index: LandmarkIndex) -> LandmarkPoint:
        return self.landmarks[index.value]


class GestureType(str, Enum):
    """Canonical 9 gestures from 04_GESTURE_ENGINE.md."""
    STOP_OR_PAUSE = "STOP_OR_PAUSE"  # Open palm
    SELECT_OR_CLICK = "SELECT_OR_CLICK"  # Pinch
    POINTER_MODE = "POINTER_MODE"  # Index point
    SCROLL_MODE = "SCROLL_MODE"  # Two fingers
    PREVIOUS = "PREVIOUS"  # Swipe left
    NEXT = "NEXT"  # Swipe right
    CONFIRM = "CONFIRM"  # Thumbs up
    CANCEL = "CANCEL"  # Thumbs down
    STOP = "STOP"  # Fist


class GestureEvent(BaseModel):
    """Gesture event schema matching 04_GESTURE_ENGINE.md."""
    type: str = "gesture"
    name: str  # maps to GestureType value or alias e.g. "PINCH"
    confidence: float
    hand: str = "right"
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    duration_ms: int = 0
