"""Structured audit logging matching 16_LOGGING_AND_AUDIT.md."""

import logging
import re
from typing import Any, Dict, List, Optional
from jarvis.core.config import JarvisConfig, LogLevel

SENSITIVE_KEY_PATTERNS = [
    re.compile(r"pass(word)?", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"auth(orization)?", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
]


def redact_sensitive_data(data: Any) -> Any:
    """Recursively scrub passwords, API keys, and secret tokens."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if any(pattern.search(str(k)) for pattern in SENSITIVE_KEY_PATTERNS):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    elif isinstance(data, str):
        # Basic check for token/key formats in raw strings
        if len(data) > 30 and any(prefix in data.lower() for prefix in ["bearer ", "eyj", "sk-"]):
            return "[REDACTED_SECRET]"
        return data
    return data


class AuditLogger:
    """Structured audit logger enforcing privacy and security logging standards."""

    def __init__(self, config: Optional[JarvisConfig] = None):
        self.config = config or JarvisConfig()
        self.audit_records: List[Dict[str, Any]] = []
        self._logger = logging.getLogger("jarvis.audit")
        self._logger.setLevel(logging.DEBUG)

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(levelname)s %(message)s")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    def log_input(
        self,
        session_id: str,
        source: str,
        source_event_id: str,
        raw_text: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> None:
        """Log raw or perceptual input respecting privacy defaults."""
        record: Dict[str, Any] = {
            "type": "input",
            "session_id": session_id,
            "source_event_id": source_event_id,
            "source": source,
        }
        if confidence is not None:
            record["confidence"] = confidence

        if self.config.logging.log_raw_speech and raw_text is not None:
            record["raw_input"] = redact_sensitive_data(raw_text)
        else:
            record["raw_input"] = "[MASKED_BY_PRIVACY_POLICY]"

        self.audit_records.append(record)
        self._logger.info(
            f"session={session_id} source_event={source_event_id} source={source} "
            f"confidence={confidence} input={record['raw_input']}"
        )

    def log_intent(
        self,
        session_id: str,
        action_id: str,
        source: str,
        intent: str,
        entities: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log intent detection result."""
        clean_entities = redact_sensitive_data(entities or {})
        record = {
            "type": "intent",
            "session_id": session_id,
            "action_id": action_id,
            "source": source,
            "intent": intent,
            "entities": clean_entities,
        }
        self.audit_records.append(record)
        formatted_entities = " ".join(f"{k}={v}" for k, v in clean_entities.items())
        msg = f"session={session_id} action={action_id} source={source} intent={intent}"
        if formatted_entities:
            msg += f" {formatted_entities}"
        self._logger.info(msg)

    def log_channel_arbitration(
        self,
        session_id: str,
        winning_channel: str,
        discarded_channel: str,
        reason: str,
    ) -> None:
        """Log multi-modal conflict resolution winner per 02_COMMAND_ROUTER.md."""
        record = {
            "type": "channel_arbitration",
            "session_id": session_id,
            "winning_channel": winning_channel,
            "discarded_channel": discarded_channel,
            "reason": reason,
        }
        self.audit_records.append(record)
        self._logger.info(
            f"session={session_id} conflict_resolution winning_channel={winning_channel} "
            f"discarded={discarded_channel} reason='{reason}'"
        )

    def log_policy_decision(
        self,
        session_id: str,
        action_id: str,
        risk: str,
        requires_confirmation: bool,
        confirmed: Optional[bool] = None,
    ) -> None:
        """Log safety policy check and confirmation outcome."""
        record = {
            "type": "policy",
            "session_id": session_id,
            "action_id": action_id,
            "risk": risk,
            "requires_confirmation": requires_confirmation,
            "confirmed": confirmed,
        }
        self.audit_records.append(record)
        self._logger.info(
            f"session={session_id} action={action_id} risk={risk} "
            f"requires_confirmation={requires_confirmation} confirmed={confirmed}"
        )

    def log_action_result(
        self,
        session_id: str,
        action_id: str,
        tool: str,
        status: str,
        verified: bool,
        result: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """Log action execution and verification result."""
        record = {
            "type": "action_result",
            "session_id": session_id,
            "action_id": action_id,
            "tool": tool,
            "status": status,
            "verified": verified,
            "result": redact_sensitive_data(result),
            "error_code": error_code,
        }
        self.audit_records.append(record)
        self._logger.info(
            f"session={session_id} action={action_id} tool={tool} status={status} "
            f"verified={verified} error_code={error_code}"
        )

    def log_security(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log security event."""
        clean_details = redact_sensitive_data(details or {})
        record = {
            "type": "security",
            "message": message,
            "details": clean_details,
        }
        self.audit_records.append(record)
        self._logger.warning(f"SECURITY: {message} {clean_details}")
