"""Audio and voice schemas matching 05_VOICE_ENGINE.md."""

import time
from typing import Optional
import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class AudioChunk(BaseModel):
    """Raw audio chunk stream container."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    duration_ms: int = 0
    rms_energy: float = 0.0

    @classmethod
    def from_numpy(cls, samples: np.ndarray, sample_rate: int = 16000) -> "AudioChunk":
        """Compute RMS and create chunk from numpy array."""
        samples_f = samples.astype(np.float32)
        rms = float(np.sqrt(np.mean(samples_f**2))) if len(samples_f) > 0 else 0.0
        pcm_bytes = (samples_f * 32767).astype(np.int16).tobytes()
        duration_ms = int((len(samples) / sample_rate) * 1000)
        return cls(
            data=pcm_bytes,
            sample_rate=sample_rate,
            channels=1,
            duration_ms=duration_ms,
            rms_energy=rms,
        )


class VoiceEvent(BaseModel):
    """Recognized speech utterance schema."""
    transcript: str
    confidence: float = 1.0
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    duration_ms: int = 0
    has_wake_word: bool = False
