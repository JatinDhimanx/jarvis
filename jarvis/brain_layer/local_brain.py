"""Offline Brain and local structured intent reasoner matching 06_OFFLINE_BRAIN.md."""

import re
from typing import Any, Dict, List, Optional
from jarvis.brain_layer.models import LLMResponse, PlanStep


class LocalBrain:
    """Local offline reasoning engine emitting structured intents without raw OS execution."""

    def analyze(self, user_prompt: str) -> LLMResponse:
        """Decompose natural-language prompt into structured intent and planned steps."""
        text = user_prompt.strip()
        lower = text.lower()

        # Multi-step pattern: "open <app>, create <file>, and write <content>"
        multi_step_match = re.search(
            r"^open\s+([^,]+),\s*(?:create\s+(?:a\s+)?(?:file\s+)?([^,]+)),?\s*(?:and\s+write\s+(.+))?$",
            text,
            re.IGNORECASE,
        )
        if multi_step_match:
            app_name = multi_step_match.group(1).strip()
            filename = multi_step_match.group(2).strip()
            content = multi_step_match.group(3).strip() if multi_step_match.group(3) else ""

            steps = [
                {"action": "open_app", "parameters": {"app_name": app_name}},
                {"action": "create_file", "parameters": {"path": filename, "content": content}},
            ]
            if content:
                steps.append({"action": "type_text", "parameters": {"text": content}})

            return LLMResponse(
                intent="MULTI_STEP_TASK",
                entities={"app_name": app_name, "file": filename},
                suggested_steps=steps,
                reply_text=f"Plan generated: Open {app_name}, create {filename}.",
                is_online=False,
            )

        # Composite pattern: "Open <app> and search for <query>"
        search_composite = re.search(r"^open\s+(.+?)\s+and\s+search\s+(?:the\s+web\s+for|for)?\s*(.+)$", text, re.IGNORECASE)
        if search_composite:
            app = search_composite.group(1).strip()
            query = search_composite.group(2).strip()
            return LLMResponse(
                intent="WEB_SEARCH",
                entities={"application": app, "query": query},
                suggested_steps=[
                    {"action": "open_app", "parameters": {"app_name": app}},
                    {"action": "search_web", "parameters": {"query": query}},
                ],
                reply_text=f"Searching for '{query}' using {app}.",
                is_online=False,
            )

        # General conversational inquiry
        return LLMResponse(
            intent="CONVERSATION",
            entities={"query": text},
            suggested_steps=[],
            reply_text=f"Understood: '{text}'. Processing locally.",
            is_online=False,
        )
