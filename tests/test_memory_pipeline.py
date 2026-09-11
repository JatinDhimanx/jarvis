"""Integration tests for memory pipeline commands."""

import pytest
from jarvis.pipeline import ExecutionPipeline
from jarvis.router.router import InputEvent


def test_pipeline_remember_recall_forget_flow():
    pipeline = ExecutionPipeline()

    # 1. Remember command
    ev1 = InputEvent(
        event_id="e-mem-1",
        channel="voice",
        raw_payload="remember that my browser is Chrome",
        confidence=0.96,
    )
    res1 = pipeline.process_event(ev1)
    assert res1["status"] == "success"
    assert res1["verified"] is True
    assert pipeline.memory_store.read("browser") is not None
    assert pipeline.memory_store.read("browser").value == "Chrome"

    # 2. Recall command
    ev2 = InputEvent(
        event_id="e-mem-2",
        channel="voice",
        raw_payload="what is my browser",
        confidence=0.94,
    )
    res2 = pipeline.process_event(ev2)
    assert res2["status"] == "success"
    assert res2["verified"] is True
    assert "Chrome" in res2["response_text"]

    # 3. Forget command
    ev3 = InputEvent(
        event_id="e-mem-3",
        channel="voice",
        raw_payload="forget my browser",
        confidence=0.95,
    )
    res3 = pipeline.process_event(ev3)
    assert res3["status"] == "success"
    assert res3["verified"] is True
    assert pipeline.memory_store.read("browser") is None
