"""Hybrid Brain manager enforcing offline-first with online fallback matching 06_OFFLINE_BRAIN.md and 07_ONLINE_BRAIN.md."""

from typing import Optional
from jarvis.brain_layer.local_brain import LocalBrain
from jarvis.brain_layer.models import LLMResponse
from jarvis.brain_layer.online_brain import OnlineBrain
from jarvis.core.config import JarvisConfig
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.logging import AuditLogger


class HybridBrainManager:
    """Coordinates local deterministic reasoning and online cloud fallback."""

    def __init__(
        self,
        config: Optional[JarvisConfig] = None,
        local_brain: Optional[LocalBrain] = None,
        online_brain: Optional[OnlineBrain] = None,
        logger: Optional[AuditLogger] = None,
    ):
        self.config = config or JarvisConfig()
        self.local_brain = local_brain or LocalBrain()
        self.online_brain = online_brain or OnlineBrain()
        self.logger = logger

    def process(self, prompt: str, force_online: bool = False) -> LLMResponse:
        """Process user request following the offline-first rule.
        
        Priority:
        1. Local deterministic / offline reasoning.
        2. Online cloud reasoning if required and enabled.
        3. Graceful downgrade if online fails (never fabricate results).
        """
        needs_online = force_online or ("today's weather" in prompt.lower() or "latest news" in prompt.lower())

        # Check offline-first rule
        if not needs_online or (self.config.mode.prefer_offline and not force_online):
            if self.config.mode.offline_enabled:
                return self.local_brain.analyze(prompt)

        # Online path
        if self.config.mode.online_enabled:
            try:
                return self.online_brain.query(prompt)
            except JarvisError as e:
                if e.code == ErrorCode.E600:
                    if self.logger:
                        self.logger.log_security(
                            f"Online service unreachable, degrading gracefully: {str(e)}"
                        )
                    # Check if offline alternative exists
                    if self.config.mode.offline_enabled:
                        local_resp = self.local_brain.analyze(prompt)
                        local_resp.reply_text = (
                            f"Network connection failed ({e.code.value}). Proceeding with offline capabilities."
                        )
                        return local_resp
                    raise

        # If online disabled or unavailable
        if self.config.mode.offline_enabled:
            return self.local_brain.analyze(prompt)

        raise JarvisError(ErrorCode.E400, "Both offline and online brains are disabled")
