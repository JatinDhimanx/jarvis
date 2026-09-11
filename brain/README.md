# JARVIS Brain

This folder defines the intelligence, behavior, tools, safety rules, context handling, and execution contracts for a personal hybrid JARVIS.

## Goals
- Work offline and online.
- Accept voice, hand gestures, keyboard, and future input methods.
- Convert natural-language requests into safe, structured actions.
- Maintain short-term context and optional long-term memory.
- Prefer deterministic local actions when possible.
- Use online AI/search only when needed and available.
- Never silently perform destructive or sensitive actions.

## Core principle

Input -> Understand -> Plan -> Validate -> Execute -> Verify -> Report

## Documents
- `01_SYSTEM_ARCHITECTURE.md` — overall architecture and component boundaries.
- `02_COMMAND_ROUTER.md` — intent detection and routing.
- `03_CONTEXT_AND_MEMORY.md` — conversation/context/memory rules.
- `04_GESTURE_ENGINE.md` — hand gesture vocabulary and confidence handling.
- `05_VOICE_ENGINE.md` — wake word, speech recognition, and speech output.
- `06_OFFLINE_BRAIN.md` — offline-first behavior and local AI.
- `07_ONLINE_BRAIN.md` — online capabilities and fallback rules.
- `08_ACTION_ENGINE.md` — computer-control action contracts.
- `09_TOOL_REGISTRY.md` — tool discovery, schemas, and permissions.
- `10_PLANNER.md` — multi-step planning.
- `11_SAFETY_AND_PERMISSIONS.md` — confirmation and dangerous-action policy.
- `12_MEMORY_SCHEMA.md` — structured memory format.
- `13_RESPONSE_STYLE.md` — JARVIS personality and response rules.
- `14_ERROR_RECOVERY.md` — failure detection and recovery.
- `15_STATE_MACHINE.md` — runtime states.
- `16_LOGGING_AND_AUDIT.md` — observability and audit trail.
- `17_CONFIG_SCHEMA.md` — configuration contract.
- `18_FEATURE_ROADMAP.md` — implementation roadmap.
- `19_COMMAND_EXAMPLES.md` — canonical examples.
- `20_DEVELOPER_CONTRACT.md` — rules for future AI agents modifying this project.

## Non-goals
The brain must not:
- invent tool results;
- claim an action succeeded without verification;
- bypass OS/security permissions;
- delete, purchase, send, publish, or expose sensitive data without the required confirmation;
- treat low-confidence gestures as commands.

## Source of truth
When behavior conflicts, use this priority:
1. Safety and permissions
2. Current user instruction
3. Explicit tool constraints
4. Current context
5. Configured preferences
6. General defaults
