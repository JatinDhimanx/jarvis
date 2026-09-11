"""Integration tests for web and browser pipeline execution."""

import pytest
from jarvis.execution.actions.browser import VirtualBrowser
from jarvis.execution.actions.web_search import WebSearchBackend
from jarvis.execution.actions.api_client import ExternalAPIClient
from jarvis.pipeline import ExecutionPipeline
from jarvis.router.router import InputEvent


def test_pipeline_web_search_flow():
    pipeline = ExecutionPipeline()
    event = InputEvent(
        event_id="e-web-1",
        channel="voice",
        raw_payload="search the web for artificial intelligence",
        confidence=0.95,
    )
    result = pipeline.process_event(event)
    assert result["status"] == "success"
    assert result["verified"] is True
    assert "artificial intelligence" in result["response_text"].lower() or "artificial intelligence" in str(pipeline.web_search_backend.last_results)


def test_pipeline_weather_query_flow():
    pipeline = ExecutionPipeline()
    event = InputEvent(
        event_id="e-web-2",
        channel="voice",
        raw_payload="weather in Berlin",
        confidence=0.92,
    )
    result = pipeline.process_event(event)
    assert result["status"] == "success"
    assert result["verified"] is True
    assert pipeline.api_client.last_weather_request["location"].lower() == "berlin"


def test_pipeline_browser_navigation_flow():
    pipeline = ExecutionPipeline()
    event = InputEvent(
        event_id="e-web-3",
        channel="voice",
        raw_payload="navigate to https://en.wikipedia.org",
        confidence=0.98,
    )
    result = pipeline.process_event(event)
    assert result["status"] == "success"
    assert result["verified"] is True
    assert pipeline.browser.current_url == "https://en.wikipedia.org"
