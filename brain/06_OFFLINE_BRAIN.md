# Offline Brain

## Purpose
Keep essential JARVIS functions available without internet.

## Offline capabilities
- gesture recognition
- voice recognition
- text-to-speech
- app launching
- keyboard/mouse automation
- window control
- media control
- local file operations
- local system status
- local LLM reasoning if installed

## Offline-first rule
Before requesting network access, ask:
1. Can this be completed deterministically locally?
2. Can an installed local model solve it?
3. Is current external information actually required?

## Local AI
A local LLM may be used for:
- intent extraction
- command normalization
- planning
- conversation
- summarization

It must not be trusted to directly execute arbitrary shell commands. It should output structured intents that pass through policy validation.
