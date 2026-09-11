"""Geometric rule-based classifier for 9 canonical gestures matching 04_GESTURE_ENGINE.md."""

import math
from typing import Dict, List, Optional, Tuple
from jarvis.perception.gesture.models import (
    GestureType,
    HandLandmarks,
    LandmarkIndex,
    LandmarkPoint,
)


def euclidean_distance(p1: LandmarkPoint, p2: LandmarkPoint) -> float:
    """Calculate 3D Euclidean distance between two landmark points."""
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)


class GestureClassifier:
    """Classifies 21 3D hand landmarks into canonical gestures."""

    def __init__(self, pinch_threshold: float = 0.065, swipe_velocity_threshold: float = 0.12):
        self.pinch_threshold = pinch_threshold
        self.swipe_velocity_threshold = swipe_velocity_threshold

    def is_finger_extended(self, hand: HandLandmarks, tip_idx: LandmarkIndex, pip_idx: LandmarkIndex) -> bool:
        """Check if a finger is extended away from the wrist relative to its PIP joint."""
        wrist = hand.get(LandmarkIndex.WRIST)
        tip = hand.get(tip_idx)
        pip = hand.get(pip_idx)
        return euclidean_distance(wrist, tip) > euclidean_distance(wrist, pip) and tip.y < pip.y

    def is_thumb_extended(self, hand: HandLandmarks) -> bool:
        """Check if thumb is extended outward from the hand palm/index MCP."""
        thumb_tip = hand.get(LandmarkIndex.THUMB_TIP)
        thumb_ip = hand.get(LandmarkIndex.THUMB_IP)
        index_mcp = hand.get(LandmarkIndex.INDEX_FINGER_MCP)
        return euclidean_distance(index_mcp, thumb_tip) > euclidean_distance(index_mcp, thumb_ip)

    def classify_static(self, hand: HandLandmarks) -> Tuple[Optional[GestureType], float]:
        """Classify a single static frame of hand landmarks into a canonical gesture.
        
        Returns:
            Tuple of (GestureType or None, confidence float).
        """
        thumb_tip = hand.get(LandmarkIndex.THUMB_TIP)
        index_tip = hand.get(LandmarkIndex.INDEX_FINGER_TIP)
        thumb_mcp = hand.get(LandmarkIndex.THUMB_MCP)
        wrist = hand.get(LandmarkIndex.WRIST)

        # Finger extension states
        index_ext = self.is_finger_extended(hand, LandmarkIndex.INDEX_FINGER_TIP, LandmarkIndex.INDEX_FINGER_PIP)
        middle_ext = self.is_finger_extended(hand, LandmarkIndex.MIDDLE_FINGER_TIP, LandmarkIndex.MIDDLE_FINGER_PIP)
        ring_ext = self.is_finger_extended(hand, LandmarkIndex.RING_FINGER_TIP, LandmarkIndex.RING_FINGER_PIP)
        pinky_ext = self.is_finger_extended(hand, LandmarkIndex.PINKY_TIP, LandmarkIndex.PINKY_PIP)
        thumb_ext = self.is_thumb_extended(hand)

        curled_fingers = [not index_ext, not middle_ext, not ring_ext, not pinky_ext]
        all_four_curled = all(curled_fingers)

        # 1. Fist (STOP)
        if all_four_curled and not thumb_ext:
            confidence = 0.96
            return GestureType.STOP, confidence

        # 2. Thumbs Up (CONFIRM)
        if all_four_curled and thumb_tip.y < thumb_mcp.y - 0.05 and thumb_ext:
            confidence = 0.95
            return GestureType.CONFIRM, confidence

        # 3. Thumbs Down (CANCEL)
        if all_four_curled and thumb_tip.y > thumb_mcp.y + 0.05 and thumb_ext:
            confidence = 0.95
            return GestureType.CANCEL, confidence

        # 4. Pinch detection: Distance between thumb tip and index tip (when not a fist)
        pinch_dist = euclidean_distance(thumb_tip, index_tip)
        if pinch_dist < self.pinch_threshold:
            confidence = max(0.85, min(0.99, 1.0 - (pinch_dist / self.pinch_threshold) * 0.15))
            return GestureType.SELECT_OR_CLICK, confidence

        # 5. Open Palm (STOP_OR_PAUSE)
        if index_ext and middle_ext and ring_ext and pinky_ext and thumb_ext:
            confidence = 0.97
            return GestureType.STOP_OR_PAUSE, confidence

        # 6. Index Point (POINTER_MODE)
        if index_ext and not middle_ext and not ring_ext and not pinky_ext:
            confidence = 0.94
            return GestureType.POINTER_MODE, confidence

        # 7. Two Fingers (SCROLL_MODE)
        if index_ext and middle_ext and not ring_ext and not pinky_ext:
            confidence = 0.93
            return GestureType.SCROLL_MODE, confidence

        return None, 0.0

    def classify_motion(
        self,
        recent_wrist_positions: List[Tuple[int, LandmarkPoint]],  # list of (timestamp_ms, point)
    ) -> Optional[Tuple[GestureType, float]]:
        """Classify dynamic motion gestures (Swipe Left / Swipe Right)."""
        if len(recent_wrist_positions) < 3:
            return None

        # Calculate horizontal displacement over time window (e.g. 150-400ms)
        t_start, p_start = recent_wrist_positions[0]
        t_end, p_end = recent_wrist_positions[-1]
        dt = (t_end - t_start) / 1000.0  # in seconds

        if dt <= 0.05 or dt > 0.60:
            return None

        dx = p_end.x - p_start.x
        vx = dx / dt

        if vx > self.swipe_velocity_threshold:
            confidence = min(0.98, 0.85 + abs(vx) * 0.1)
            return GestureType.NEXT, confidence
        elif vx < -self.swipe_velocity_threshold:
            confidence = min(0.98, 0.85 + abs(vx) * 0.1)
            return GestureType.PREVIOUS, confidence

        return None
