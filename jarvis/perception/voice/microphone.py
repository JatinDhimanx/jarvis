"""Microphone capture abstraction matching 05_VOICE_ENGINE.md."""

from abc import ABC, abstractmethod
from queue import Empty, Queue
import threading
from typing import Optional
import numpy as np

from jarvis.perception.voice.models import AudioChunk


class MicrophoneInterface(ABC):
    """Abstract interface for audio capture from microphone."""

    @abstractmethod
    def start(self) -> bool:
        """Open microphone stream."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Close microphone stream."""
        pass

    @abstractmethod
    def read_chunk(self, timeout_ms: int = 100) -> Optional[AudioChunk]:
        """Read next available audio chunk."""
        pass

    @property
    @abstractmethod
    def is_active(self) -> bool:
        pass


class SoundDeviceMicrophone(MicrophoneInterface):
    """Hardware microphone capture using sounddevice."""

    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._queue: Queue[AudioChunk] = Queue()
        self._stream = None
        self._lock = threading.Lock()
        self._is_active = False

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            pass
        chunk = AudioChunk.from_numpy(indata[:, 0], sample_rate=self.sample_rate)
        self._queue.put(chunk)

    def start(self) -> bool:
        with self._lock:
            if self._is_active and self._stream is not None:
                return True
            try:
                import sounddevice as sd
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=self.chunk_size,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._is_active = True
                return True
            except Exception:
                self._stream = None
                self._is_active = False
                return False

    def stop(self) -> None:
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self._is_active = False

    def read_chunk(self, timeout_ms: int = 100) -> Optional[AudioChunk]:
        try:
            return self._queue.get(timeout=timeout_ms / 1000.0)
        except Empty:
            return None

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._is_active


class MockMicrophone(MicrophoneInterface):
    """Mock microphone for automated headless testing."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._queue: Queue[AudioChunk] = Queue()
        self._is_active = False

    def inject_chunk(self, chunk: AudioChunk) -> None:
        self._queue.put(chunk)

    def inject_samples(self, samples: np.ndarray) -> None:
        chunk = AudioChunk.from_numpy(samples, sample_rate=self.sample_rate)
        self._queue.put(chunk)

    def start(self) -> bool:
        self._is_active = True
        return True

    def stop(self) -> None:
        self._is_active = False

    def read_chunk(self, timeout_ms: int = 100) -> Optional[AudioChunk]:
        if not self._is_active:
            return None
        try:
            return self._queue.get(timeout=timeout_ms / 1000.0)
        except Empty:
            return None

    @property
    def is_active(self) -> bool:
        return self._is_active
