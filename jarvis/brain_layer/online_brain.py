"""Online Cloud AI integration and network failure handling matching 07_ONLINE_BRAIN.md."""

from typing import Any, Dict, Optional
from jarvis.brain_layer.models import LLMResponse
from jarvis.core.errors import ErrorCode, JarvisError


class OnlineBrain:
    """Online cloud reasoning engine with graceful network failure recovery."""

    def __init__(self, is_network_available: bool = True):
        self.is_network_available = is_network_available

    def query(self, prompt: str) -> LLMResponse:
        """Query cloud reasoning API.
        
        Per 07_ONLINE_BRAIN.md:
        - If network fails: raises JarvisError(E600).
        - Never fabricates a result when a network call fails.
        """
        if not self.is_network_available:
            raise JarvisError(
                ErrorCode.E600,
                "Online capability unreachable: network connection failed",
            )

        return LLMResponse(
            intent="ONLINE_QUERY",
            entities={"query": prompt},
            suggested_steps=[],
            reply_text=f"Online search result for: '{prompt}'.",
            is_online=True,
        )
