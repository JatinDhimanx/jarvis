"""Wake word detector matching 05_VOICE_ENGINE.md."""

import re
from typing import Optional, Tuple


class WakeWordDetector:
    """Detects configured wake word in speech and normalizes command payload."""

    def __init__(self, wake_word: str = "jarvis"):
        self.wake_word = wake_word.strip().lower()
        self._pattern = re.compile(rf"\b(hey\s+)?{re.escape(self.wake_word)}\b[,:\s]*", re.IGNORECASE)

    def check_text(self, text: str) -> Tuple[bool, str]:
        """Check if text contains the wake word and return (has_wake_word, stripped_text)."""
        match = self._pattern.search(text)
        if match:
            # Strip the wake word prefix
            cleaned = self._pattern.sub("", text).strip()
            return True, cleaned
        return False, text.strip()
