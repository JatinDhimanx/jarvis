"""Voice Activity Detection and silence timeout tracker matching 05_VOICE_ENGINE.md."""

from jarvis.perception.voice.models import AudioChunk


class VoiceActivityDetector:
    """Detects presence of human voice and tracks continuous silence duration."""

    def __init__(self, energy_threshold: float = 0.015, silence_timeout_ms: int = 2500):
        self.energy_threshold = energy_threshold
        self.silence_timeout_ms = silence_timeout_ms
        self.continuous_silence_ms: int = 0
        self.is_speech_active: bool = False

    def reset(self) -> None:
        """Reset silence tracker."""
        self.continuous_silence_ms = 0
        self.is_speech_active = False

    def process_chunk(self, chunk: AudioChunk) -> tuple[bool, bool]:
        """Process an audio chunk.
        
        Returns:
            Tuple of (is_voice_present: bool, has_silence_timed_out: bool)
        """
        is_voice = chunk.rms_energy >= self.energy_threshold
        chunk_duration = chunk.duration_ms or 64

        if is_voice:
            self.is_speech_active = True
            self.continuous_silence_ms = 0
        else:
            if self.is_speech_active:
                self.continuous_silence_ms += chunk_duration

        silence_timed_out = (
            self.is_speech_active
            and self.continuous_silence_ms >= self.silence_timeout_ms
        )

        return is_voice, silence_timed_out
