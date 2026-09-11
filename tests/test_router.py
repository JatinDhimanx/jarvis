"""Tests for CommandRouter and multi-modal conflict resolution matching 02_COMMAND_ROUTER.md."""

import time
import pytest

from jarvis.core.logging import AuditLogger
from jarvis.router.intents import ActionGroup, Intent, INTENT_TO_ACTION_GROUP
from jarvis.router.router import CommandRouter, InputEvent


def test_intent_to_action_group_table_completeness():
    """Verify all intents have an explicit action group in the mapping table."""
    for intent in Intent:
        assert intent in INTENT_TO_ACTION_GROUP
        assert isinstance(INTENT_TO_ACTION_GROUP[intent], ActionGroup)


def test_deterministic_intent_parsing():
    """Test standard voice/text commands parse to correct intent and action."""
    router = CommandRouter()

    # System controls
    ev1 = InputEvent(event_id="e1", channel="voice", raw_payload="Jarvis, set volume to 40")
    dec1 = router.route(ev1)
    assert dec1.intent == Intent.SYSTEM_CONTROL
    assert dec1.action == "set_volume"
    assert dec1.entities == {"value": 40}

    ev2 = InputEvent(event_id="e2", channel="voice", raw_payload="mute sound")
    dec2 = router.route(ev2)
    assert dec2.intent == Intent.SYSTEM_CONTROL
    assert dec2.action == "mute"
    assert dec2.entities == {"state": True}

    # App controls
    ev3 = InputEvent(event_id="e3", channel="voice", raw_payload="open Chrome")
    dec3 = router.route(ev3)
    assert dec3.intent == Intent.APP_CONTROL
    assert dec3.action == "open_app"
    assert dec3.entities == {"app_name": "Chrome"}

    # Shutdown
    ev4 = InputEvent(event_id="e4", channel="voice", raw_payload="turn off the computer")
    dec4 = router.route(ev4)
    assert dec4.intent == Intent.SYSTEM_CONTROL
    assert dec4.action == "shutdown"


def test_gesture_routing():
    """Test gesture mapping to actions."""
    router = CommandRouter()

    ev_pinch = InputEvent(event_id="g1", channel="gesture", raw_payload="PINCH")
    dec_pinch = router.route(ev_pinch)
    assert dec_pinch.intent == Intent.MOUSE_CONTROL
    assert dec_pinch.action == "click"

    ev_stop = InputEvent(event_id="g2", channel="gesture", raw_payload="STOP")
    dec_stop = router.route(ev_stop)
    assert dec_stop.is_emergency is True


def test_multimodal_emergency_wins():
    """Rule 1: Emergency stop always wins regardless of channel."""
    router = CommandRouter()
    now = int(time.time() * 1000)

    # User says "open chrome" while showing palm "STOP"
    ev_voice = InputEvent(event_id="v1", channel="voice", raw_payload="open Chrome", confidence=0.99, timestamp_ms=now)
    ev_gesture = InputEvent(event_id="g1", channel="gesture", raw_payload="STOP", confidence=0.85, timestamp_ms=now + 50)

    winner = router.resolve_multimodal([ev_voice, ev_gesture])
    assert winner.event_id == "g1"
    assert winner.channel == "gesture"


def test_multimodal_debounce_arbitration():
    """Rule 2: Debounce window arbitration picks higher confidence / recency."""
    logger = AuditLogger()
    router = CommandRouter(logger=logger, debounce_window_ms=500)
    now = int(time.time() * 1000)

    ev_voice = InputEvent(event_id="v1", channel="voice", raw_payload="open Chrome", confidence=0.95, timestamp_ms=now)
    ev_gesture = InputEvent(event_id="g1", channel="gesture", raw_payload="NEXT", confidence=0.80, timestamp_ms=now + 100)

    winner = router.resolve_multimodal([ev_voice, ev_gesture], session_id="s-test")
    assert winner.event_id == "v1"

    # Verify winning channel was logged
    arbitration_logs = [r for r in logger.audit_records if r.get("type") == "channel_arbitration"]
    assert len(arbitration_logs) == 1
    assert arbitration_logs[0]["winning_channel"] == "voice"


def test_multimodal_same_intent_deduplication():
    """Rule 3: Same intent on both channels executes once."""
    router = CommandRouter()
    now = int(time.time() * 1000)

    ev_voice = InputEvent(event_id="v1", channel="voice", raw_payload="pause", confidence=0.85, timestamp_ms=now)
    ev_gesture = InputEvent(event_id="g1", channel="gesture", raw_payload="PINCH", confidence=0.95, timestamp_ms=now + 50)

    # In our gestures, PINCH is click, not pause. Let's test two events both meaning pause / stop or next:
    ev_next_voice = InputEvent(event_id="v2", channel="voice", raw_payload="next track", confidence=0.88, timestamp_ms=now)
    ev_next_gesture = InputEvent(event_id="g2", channel="gesture", raw_payload="NEXT", confidence=0.92, timestamp_ms=now + 20)

    winner = router.resolve_multimodal([ev_next_voice, ev_next_gesture])
    assert winner.event_id == "g2"  # higher confidence wins the deduplicated slot


def test_unknown_and_ambiguous_routing():
    """Router does not fabricate non-existent actions; asks for clarification."""
    router = CommandRouter()

    # Ambiguous pronoun
    ev_ambig = InputEvent(event_id="e1", channel="voice", raw_payload="open that")
    dec_ambig = router.route(ev_ambig)
    assert dec_ambig.intent == Intent.UNKNOWN
    assert dec_ambig.requires_clarification is True
    assert "Which item" in dec_ambig.clarification_prompt

    # Nonsense
    ev_unknown = InputEvent(event_id="e2", channel="voice", raw_payload="asdfghjkl random gibberish")
    dec_unknown = router.route(ev_unknown)
    assert dec_unknown.intent == Intent.UNKNOWN
    assert dec_unknown.action is None
