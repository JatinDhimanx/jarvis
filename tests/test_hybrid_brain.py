"""Tests for Hybrid Brain and Offline-First handling matching 06_OFFLINE_BRAIN.md and 07_ONLINE_BRAIN.md."""

import pytest
from jarvis.brain_layer.hybrid_manager import HybridBrainManager
from jarvis.brain_layer.local_brain import LocalBrain
from jarvis.brain_layer.online_brain import OnlineBrain
from jarvis.core.config import JarvisConfig
from jarvis.core.errors import ErrorCode, JarvisError


def test_local_brain_multistep_parsing():
    lb = LocalBrain()
    res = lb.analyze("open notepad, create file notes.txt, and write hello world")
    assert res.intent == "MULTI_STEP_TASK"
    assert len(res.suggested_steps) == 3
    assert res.suggested_steps[0]["action"] == "open_app"
    assert res.suggested_steps[0]["parameters"]["app_name"] == "notepad"
    assert res.suggested_steps[1]["action"] == "create_file"
    assert res.suggested_steps[1]["parameters"]["path"] == "notes.txt"
    assert res.suggested_steps[2]["action"] == "type_text"
    assert res.suggested_steps[2]["parameters"]["text"] == "hello world"
    assert not res.is_online


def test_local_brain_composite_search():
    lb = LocalBrain()
    res = lb.analyze("open chrome and search for python 3.11 release notes")
    assert res.intent == "WEB_SEARCH"
    assert len(res.suggested_steps) == 2
    assert res.suggested_steps[0]["action"] == "open_app"
    assert res.suggested_steps[1]["action"] == "search_web"
    assert "python 3.11 release notes" in res.suggested_steps[1]["parameters"]["query"]


def test_local_brain_conversational():
    lb = LocalBrain()
    res = lb.analyze("how are you doing?")
    assert res.intent == "CONVERSATION"
    assert len(res.suggested_steps) == 0
    assert not res.is_online


def test_online_brain_success():
    ob = OnlineBrain(is_network_available=True)
    res = ob.query("what is quantum computing?")
    assert res.intent == "ONLINE_QUERY"
    assert res.is_online is True
    assert "quantum computing" in res.reply_text


def test_online_brain_failure_raises_e600():
    ob = OnlineBrain(is_network_available=False)
    with pytest.raises(JarvisError) as exc_info:
        ob.query("search query")
    assert exc_info.value.code == ErrorCode.E600


def test_hybrid_brain_prefers_offline():
    cfg = JarvisConfig()
    cfg.mode.offline_enabled = True
    cfg.mode.online_enabled = True
    cfg.mode.prefer_offline = True

    hybrid = HybridBrainManager(config=cfg)
    res = hybrid.process("open notepad, create file test.txt")
    assert not res.is_online
    assert res.intent == "MULTI_STEP_TASK"


def test_hybrid_brain_graceful_degradation_on_e600():
    cfg = JarvisConfig()
    cfg.mode.offline_enabled = True
    cfg.mode.online_enabled = True
    cfg.mode.prefer_offline = False  # Allows online

    # Network is unavailable
    online_brain = OnlineBrain(is_network_available=False)
    hybrid = HybridBrainManager(config=cfg, online_brain=online_brain)

    # When requesting online query, E600 triggers graceful fallback to local
    res = hybrid.process("today's weather in Tokyo", force_online=True)
    assert not res.is_online
    assert "E600" in res.reply_text or "failed" in res.reply_text.lower()


def test_hybrid_brain_both_disabled_raises_e400():
    cfg = JarvisConfig()
    cfg.mode.offline_enabled = False
    cfg.mode.online_enabled = False

    hybrid = HybridBrainManager(config=cfg)
    with pytest.raises(JarvisError) as exc_info:
        hybrid.process("hello")
    assert exc_info.value.code == ErrorCode.E400
