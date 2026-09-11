"""Text-To-Speech (TTS) engine and feedback loop echo gate matching 05_VOICE_ENGINE.md."""

from abc import ABC, abstractmethod
import threading
from typing import List, Optional


class TTSInterface(ABC):
    """Abstract interface for speech synthesis."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak response text synchronously or asynchronously."""
        pass

    @property
    @abstractmethod
    def is_speaking(self) -> bool:
        """True while TTS audio is playing through speakers (echo gate)."""
        pass


class Pyttsx3TTS(TTSInterface):
    """Offline Windows TTS engine using pyttsx3."""

    def __init__(self, rate: int = 175, volume: float = 1.0):
        self.rate = rate
        self.volume = volume
        self._is_speaking = False
        self._lock = threading.Lock()
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", self.rate)
                self._engine.setProperty("volume", self.volume)
            except Exception:
                self._engine = None
        return self._engine

    def speak(self, text: str) -> None:
        clean = text.strip()
        if not clean:
            return

        with self._lock:
            self._is_speaking = True
            try:
                engine = self._get_engine()
                if engine is not None:
                    engine.say(clean)
                    engine.runAndWait()
            except Exception:
                pass
            finally:
                self._is_speaking = False

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._is_speaking


class MockTTS(TTSInterface):
    """Mock TTS capturing spoken texts for automated verification."""

    def __init__(self):
        self.spoken_texts: List[str] = []
        self._is_speaking = False
        self._lock = threading.Lock()

    def set_speaking(self, speaking: bool) -> None:
        with self._lock:
            self._is_speaking = speaking

    def speak(self, text: str) -> None:
        with self._lock:
            self._is_speaking = True
            self.spoken_texts.append(text.strip())
            self._is_speaking = False

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._is_speaking
