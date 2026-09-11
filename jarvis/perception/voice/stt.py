"""Speech-To-Text (STT) interface and implementations matching 05_VOICE_ENGINE.md."""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from jarvis.perception.voice.models import AudioChunk


class STTInterface(ABC):
    """Abstract interface for speech transcription."""

    @abstractmethod
    def transcribe(self, chunks: List[AudioChunk]) -> Optional[str]:
        """Convert collected audio chunks into transcribed text."""
        pass


class OfflineWhisperSTT(STTInterface):
    """Offline Whisper / faster-whisper model integration."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            except Exception:
                self._model = None

    def transcribe(self, chunks: List[AudioChunk]) -> Optional[str]:
        if not chunks:
            return None
        try:
            self._load_model()
            if self._model is None:
                return None

            # Concatenate PCM bytes into float32 audio array
            raw_bytes = b"".join(c.data for c in chunks)
            audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            segments, _ = self._model.transcribe(audio_np, beam_size=1)
            text = " ".join([seg.text.strip() for seg in segments]).strip()
            return text if text else None
        except Exception:
            return None


class MockSTT(STTInterface):
    """Mock STT for headless deterministic testing."""

    def __init__(self, next_transcript: Optional[str] = None):
        self.next_transcript = next_transcript

    def set_transcript(self, text: Optional[str]) -> None:
        self.next_transcript = text

    def transcribe(self, chunks: List[AudioChunk]) -> Optional[str]:
        return self.next_transcript
