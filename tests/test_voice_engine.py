"""Tests for Voice Engine matching 05_VOICE_ENGINE.md."""

import numpy as np
import pytest

from jarvis.core.config import JarvisConfig, VoiceSection
from jarvis.core.state_machine import State, StateMachine
from jarvis.perception.voice.engine import VoiceEngine
from jarvis.perception.voice.microphone import MockMicrophone
from jarvis.perception.voice.models import AudioChunk, VoiceEvent
from jarvis.perception.voice.stt import MockSTT
from jarvis.perception.voice.tts import MockTTS
from jarvis.pipeline import ExecutionPipeline


def create_audio_chunk(duration_ms: int = 100, rms_energy: float = 0.05) -> AudioChunk:
    """Helper to create synthetic audio chunk."""
    sample_rate = 16000
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    samples = np.ones(num_samples, dtype=np.float32) * rms_energy
    return AudioChunk.from_numpy(samples, sample_rate=sample_rate)


def test_voice_privacy_always_listen_default():
    """Rule 4 & 17_CONFIG_SCHEMA.md: always_listen defaults to False."""
    cfg = JarvisConfig()
    assert cfg.voice.always_listen is False
    assert cfg.voice.enabled is True

    mock_mic = MockMicrophone()
    engine = VoiceEngine(config=cfg, microphone=mock_mic)

    # Engine start keeps mic idle when always_listen is False
    engine.start()
    assert engine.is_listening is False
    assert mock_mic.is_active is False

    # Speech without wake word is ignored
    ev = engine.process_utterance("set volume to 50")
    assert ev is None


def test_wake_word_detection_and_stripping():
    """Wake word 'Jarvis' opens listening and strips prefix."""
    cfg = JarvisConfig(voice=VoiceSection(always_listen=False, wake_word_enabled=True))
    engine = VoiceEngine(config=cfg)

    # 1. Direct wake word utterance
    ev1 = engine.process_utterance("Jarvis, set volume to 40")
    assert ev1 is not None
    assert ev1.has_wake_word is True
    assert ev1.transcript == "set volume to 40"

    # 2. 'Hey Jarvis' prefix
    ev2 = engine.process_utterance("Hey Jarvis, open Chrome")
    assert ev2 is not None
    assert ev2.has_wake_word is True
    assert ev2.transcript == "open Chrome"

    # 3. Without wake word when not in active listening
    ev3 = engine.process_utterance("turn off the computer")
    assert ev3 is None


def test_active_listening_state_and_indicator():
    """Opening listening window updates indicator callback and StateMachine."""
    sm = StateMachine()
    cfg = JarvisConfig()
    engine = VoiceEngine(config=cfg, state_machine=sm, microphone=MockMicrophone())

    indicator_history = []
    engine.set_listening_indicator_callback(lambda active: indicator_history.append(active))

    engine.open_listening_window()
    assert engine.is_listening is True
    assert sm.current_state == State.LISTENING
    assert indicator_history == [True]

    # In active listening window, speech WITHOUT wake word is accepted
    ev = engine.process_utterance("set volume to 30")
    assert ev is not None
    assert ev.transcript == "set volume to 30"

    engine.stop()
    assert engine.is_listening is False
    assert sm.current_state == State.IDLE
    assert indicator_history == [True, False]


def test_tts_feedback_loop_echo_gate():
    """Per 05_VOICE_ENGINE.md: speech from TTS playback must be ignored to prevent loops."""
    cfg = JarvisConfig()
    mock_tts = MockTTS()
    engine = VoiceEngine(config=cfg, tts=mock_tts)

    # While TTS is speaking, incoming utterances are rejected
    mock_tts.set_speaking(True)
    ev = engine.process_utterance("Jarvis, stop")
    assert ev is None

    # While TTS is speaking, incoming audio chunks are rejected
    chunk = create_audio_chunk(duration_ms=100, rms_energy=0.08)
    chunk_res = engine.process_chunk(chunk)
    assert chunk_res is None

    # When TTS finishes speaking, processing resumes normally
    mock_tts.set_speaking(False)
    ev_resumed = engine.process_utterance("Jarvis, stop")
    assert ev_resumed is not None
    assert ev_resumed.transcript == "stop"


def test_silence_timeout_closes_listening_window():
    """Silence exceeding 2500ms terminates active listening window."""
    cfg = JarvisConfig(voice=VoiceSection(silence_timeout_ms=500))  # 500ms for fast test
    sm = StateMachine()
    mock_stt = MockSTT(next_transcript="Jarvis, set volume to 60")
    engine = VoiceEngine(config=cfg, state_machine=sm, stt=mock_stt, microphone=MockMicrophone())

    engine.open_listening_window()
    assert engine.is_listening is True

    # 1. Voice chunk arrives (speech active)
    speech_chunk = create_audio_chunk(duration_ms=200, rms_energy=0.05)
    engine.process_chunk(speech_chunk)
    assert engine.is_listening is True

    # 2. Silence chunks totaling 600ms arrive (> 500ms silence timeout)
    silence_chunk = create_audio_chunk(duration_ms=300, rms_energy=0.001)
    res1 = engine.process_chunk(silence_chunk)
    assert res1 is None  # 300ms < 500ms

    res2 = engine.process_chunk(silence_chunk)  # 600ms total silence
    assert res2 is not None
    assert res2.transcript == "set volume to 60"
    assert engine.is_listening is False  # Automatically closed window


def test_end_to_end_voice_pipeline_with_tts():
    """End-to-end: Voice utterance -> VoiceEngine -> STT -> Pipeline -> Action -> TTS speaking output."""
    cfg = JarvisConfig()
    mock_tts = MockTTS()
    pipeline = ExecutionPipeline(config=cfg, tts=mock_tts)

    engine = VoiceEngine(config=cfg, tts=mock_tts)
    voice_ev = engine.process_utterance("Jarvis, set volume to 45")
    assert voice_ev is not None

    result = pipeline.process_voice(voice_ev)

    assert result["status"] == "success"
    assert result["verified"] is True
    assert result["response_text"] == "Volume set to 45%"
    # Verify TTS spoke the response text
    assert len(mock_tts.spoken_texts) == 1
    assert mock_tts.spoken_texts[0] == "Volume set to 45%"
