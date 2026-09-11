# Context and Memory

## Context layers

### L0 — Current input
The latest voice/gesture/text event.

### L1 — Current task
The active command and its intermediate results.

### L2 — Conversation context
Recent turns needed to resolve references.

### L3 — Persistent preferences
Only stable, useful preferences explicitly saved by the user.

### L4 — Project knowledge
JARVIS configuration, installed tools, capabilities, and known application mappings.

## Rules
- Do not invent memories.
- Do not save secrets such as passwords or authentication tokens.
- Do not save sensitive personal information unless explicitly designed and authorized.
- Expire temporary task context when the task ends.
- A user can override preferences in the current request.
- When context is ambiguous, ask instead of guessing.

## Reference resolution
"Close it" -> identify the most recent relevant open application/window.
"Search that" -> identify the most recent search target.
"Do it again" -> repeat only the last reversible action.

## Memory operations
`READ`, `WRITE`, `UPDATE`, `FORGET`, `CLEAR_TASK_CONTEXT`.

Every persistent-memory write should record:
- key
- value
- source
- timestamp
- confidence
- user authorization
