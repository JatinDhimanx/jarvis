"""Tests for Media actions matching 08_ACTION_ENGINE.md."""

import pytest
from jarvis.execution.action_engine import ActionRequest, ActionStatus
from jarvis.execution.actions.media import VirtualMediaManager
from jarvis.pipeline import ExecutionPipeline


def test_media_playback_controls():
    """Test play/pause, next track, and previous track."""
    mm = VirtualMediaManager()

    # play_pause toggle
    res1 = mm.play_pause()
    assert "playing" in res1
    assert mm.is_playing is True

    res2 = mm.play_pause()
    assert "paused" in res2
    assert mm.is_playing is False

    # next_track
    track_initial = mm.current_track_idx
    mm.next_track()
    assert mm.current_track_idx == (track_initial + 1) % len(mm.playlist)

    # previous_track
    mm.previous_track()
    assert mm.current_track_idx == track_initial


def test_media_pipeline_execution():
    """Test media actions via pipeline."""
    mm = VirtualMediaManager()
    pipeline = ExecutionPipeline(media_manager=mm)

    req = ActionRequest(
        action_id="a-med1",
        session_id="s-test",
        source_event_id="e-test",
        source="gesture",
        action="next_track",
    )
    result = pipeline.action_engine.execute(req)
    assert result.status == ActionStatus.SUCCESS
    assert result.verified is True
    assert "Playing next track" in result.result
