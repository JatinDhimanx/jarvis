"""Camera capture abstraction matching 04_GESTURE_ENGINE.md."""

from abc import ABC, abstractmethod
import threading
from typing import Any, Optional
import numpy as np


class CameraInterface(ABC):
    """Abstract interface for camera video frames."""

    @abstractmethod
    def start(self) -> bool:
        """Initialize and start camera capture. Returns True if successful."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Release camera and resources."""
        pass

    @abstractmethod
    def read_frame(self) -> Optional[np.ndarray]:
        """Read latest frame, or None if unavailable."""
        pass

    @property
    @abstractmethod
    def is_active(self) -> bool:
        pass


class OpenCVCamera(CameraInterface):
    """Real camera implementation using OpenCV VideoCapture."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self._cap: Optional[Any] = None
        self._lock = threading.Lock()
        self._is_active = False

    def start(self) -> bool:
        with self._lock:
            if self._is_active and self._cap is not None:
                return True
            try:
                import cv2
                self._cap = cv2.VideoCapture(self.camera_index)
                if self._cap.isOpened():
                    self._is_active = True
                    return True
                self._cap.release()
                self._cap = None
                return False
            except Exception:
                self._cap = None
                self._is_active = False
                return False

    def stop(self) -> None:
        with self._lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None
            self._is_active = False

    def read_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if not self._is_active or self._cap is None:
                return None
            ret, frame = self._cap.read()
            if ret:
                return frame
            return None

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._is_active


class MockCamera(CameraInterface):
    """Mock camera for automated testing and headless environments."""

    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self._active = False
        self.next_frame: Optional[np.ndarray] = None

    def start(self) -> bool:
        self._active = True
        return True

    def stop(self) -> None:
        self._active = False

    def read_frame(self) -> Optional[np.ndarray]:
        if not self._active:
            return None
        if self.next_frame is not None:
            return self.next_frame
        # Return blank synthetic RGB frame
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    @property
    def is_active(self) -> bool:
        return self._active
