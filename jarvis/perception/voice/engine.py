"""Voice Engine coordinating microphone, VAD, wake word, STT, and TTS matching 05_VOICE_ENGINE.md."""

import time
from typing import Callable, List, Optional
import uuid

from jarvis.core.config import JarvisConfig
from jarvis.core.logging import AuditLogger
from jarvis.core.state_machine import State, StateMachine
from jarvis.perception.voice.microphone import (
    MicrophoneInterface,
    MockMicrophone,
    SoundDeviceMicrophone,
)
from jarvis.perception.voice.models import AudioChunk, VoiceEvent
from jarvis.perception.voice.stt import MockSTT, OfflineWhisperSTT, STTInterface
from jarvis.perception.voice.tts import MockTTS, Pyttsx3TTS, TTSInterface
from jarvis.perception.voice.vad import VoiceActivityDetector
from jarvis.perception.voice.wake_word import WakeWordDetector
from jarvis.router.router import InputEvent


class VoiceEngine:
    """Voice perception and output engine enforcing privacy defaults and feedback loop protection."""

    def __init__(
        self,
        config: Optional[JarvisConfig] = None,
        microphone: Optional[MicrophoneInterface] = None,
        stt: Optional[STTInterface] = None,
        tts: Optional[TTSInterface] = None,
        state_machine: Optional[StateMachine] = None,
        logger: Optional[AuditLogger] = None,
    ):
        self.config = config or JarvisConfig()
        self.microphone = microphone
        self.stt = stt
        self.tts = tts or MockTTS()
        self.state_machine = state_machine
        self.logger = logger

        self.vad = VoiceActivityDetector(silence_timeout_ms=self.config.voice.silence_timeout_ms)
        self.wake_word_detector = WakeWordDetector(wake_word=self.config.jarvis.wake_word)

        self._is_active_listening: bool = False
        self._audio_buffer: List[AudioChunk] = []
        self._listening_indicator_callback: Optional[Callable[[bool], None]] = None

    @property
    def is_listening(self) -> bool:
        return self._is_active_listening

    def set_listening_indicator_callback(self, callback: Callable[[bool], None]) -> None:
        """Register a callback for UI/HUD listening state indicator."""
        self._listening_indicator_callback = callback

    def _set_listening_state(self, active: bool) -> None:
        self._is_active_listening = active
        if self._listening_indicator_callback:
            self._listening_indicator_callback(active)

        if self.state_machine:
            if active and self.state_machine.current_state == State.IDLE:
                self.state_machine.transition_to(State.LISTENING)
            elif not active and self.state_machine.current_state == State.LISTENING:
                self.state_machine.transition_to(State.IDLE)

    def start(self) -> bool:
        """Start microphone stream if voice is enabled and always_listen is true, or on-demand."""
        if not self.config.voice.enabled:
            return False

        if self.microphone is None:
            self.microphone = SoundDeviceMicrophone()

        # If always_listen is true, open mic now
        if self.config.voice.always_listen:
            started = self.microphone.start()
            self._set_listening_state(True)
            return started

        # Default privacy: mic remains idle until explicitly triggered
        return True

    def stop(self) -> None:
        """Stop microphone capture and clear buffers."""
        if self.microphone is not None:
            self.microphone.stop()
        self._set_listening_state(False)
        self._audio_buffer.clear()
        self.vad.reset()

    def open_listening_window(self) -> bool:
        """Explicitly open active listening window (e.g. push-to-talk or wake word trigger)."""
        if not self.config.voice.enabled:
            return False

        if self.microphone is None:
            self.microphone = SoundDeviceMicrophone()

        if not self.microphone.is_active:
            self.microphone.start()

        self._set_listening_state(True)
        self.vad.reset()
        self._audio_buffer.clear()
        return True

    def process_chunk(self, chunk: AudioChunk) -> Optional[VoiceEvent]:
        """Process an incoming audio chunk through feedback loop gate, VAD, and STT."""
        # 1. TTS Feedback Loop Prevention per 05_VOICE_ENGINE.md
        # Distinguish user speech from TTS playback: ignore audio while JARVIS is speaking
        if self.tts and self.tts.is_speaking:
            return None

        # 2. Check if active listening window is open
        if not self._is_active_listening and not self.config.voice.always_listen:
            # When always_listen is false and listening window is closed, audio is not buffered
            return None

        # 3. VAD processing & silence tracking
        is_voice, silence_timed_out = self.vad.process_chunk(chunk)

        if is_voice or self._is_active_listening:
            self._audio_buffer.append(chunk)

        # 4. Check silence timeout per 05_VOICE_ENGINE.md
        if silence_timed_out:
            # Silence timeout reached; close listening window and transcribe collected speech
            collected = list(self._audio_buffer)
            self._audio_buffer.clear()
            self.vad.reset()
            self._set_listening_state(False)

            if collected:
                return self._transcribe_and_validate(collected)
            return None

        return None

    def process_utterance(self, text: str, confidence: float = 0.95) -> Optional[VoiceEvent]:
        """Process a direct or mocked speech utterance through wake-word and privacy gates."""
        # TTS feedback loop protection
        if self.tts and self.tts.is_speaking:
            return None

        has_wake_word, cleaned_text = self.wake_word_detector.check_text(text)

        # Rule: Ignore speech outside active listening window unless wake word is present
        if not self._is_active_listening and not self.config.voice.always_listen:
            if not (self.config.voice.wake_word_enabled and has_wake_word):
                return None

        return VoiceEvent(
            transcript=cleaned_text if has_wake_word else text.strip(),
            confidence=confidence,
            has_wake_word=has_wake_word,
        )

    def _transcribe_and_validate(self, chunks: List[AudioChunk]) -> Optional[VoiceEvent]:
        """Run STT on audio chunks and evaluate wake word and transcript."""
        if self.stt is None:
            self.stt = OfflineWhisperSTT()

        transcript = self.stt.transcribe(chunks)
        if not transcript:
            return None

        return self.process_utterance(transcript)

    def to_input_event(self, voice_event: VoiceEvent, event_id: Optional[str] = None) -> InputEvent:
        """Convert a VoiceEvent into a normalized router InputEvent."""
        eid = event_id or f"v-{uuid.uuid4().hex[:6]}"
        return InputEvent(
            event_id=eid,
            channel="voice",
            raw_payload=voice_event.transcript,
            confidence=voice_event.confidence,
            timestamp_ms=voice_event.timestamp_ms,
        )

    def speak(self, text: str) -> None:
        """Speak response text using TTS with feedback loop protection."""
        if self.tts:
            self.tts.speak(text)
