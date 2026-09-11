# Changelog

## v1.1 — Refinement pass

The original 20-document brain was well-structured but had gaps that would surface as soon as it was implemented. This pass closes them without changing the overall design:

1. **02_COMMAND_ROUTER.md** — added an explicit Intent -> Action-group mapping table. Previously intents (`SYSTEM_CONTROL`, etc.) and action functions (`set_volume`, etc.) were defined in separate docs with no link between them.
2. **02_COMMAND_ROUTER.md** — added multi-modal conflict resolution rules for when voice and gesture fire close together (emergency-stop priority, debounce window, duplicate-intent dedup).
3. **08_ACTION_ENGINE.md** — action schema now carries `action_id`, `session_id`, `source_event_id`, `source`, `timestamp` for traceability, and clarifies that `requires_confirmation` is derived deterministically from risk + config, never asserted ad hoc. Result schema carries `error_code`.
4. **04_GESTURE_ENGINE.md** — separated "risk of the gesture event" (false-positive trigger) from "risk of the action it confirms/triggers"; fixed `CONFIRM` (thumbs up) being mislabeled Medium when the gesture itself is low-risk.
5. **04_GESTURE_ENGINE.md / 05_VOICE_ENGINE.md** — added explicit privacy defaults: camera/mic off or idle until the user opts in; visible active-indicator requirement.
6. **14_ERROR_RECOVERY.md** — replaced free-text error classes with a stable numbered code table (`E100`–`E700`) so logs/UI/TTS can reference errors consistently.
7. **17_CONFIG_SCHEMA.md** — added `vision.enabled` (default false), `voice.always_listen` (default false), `vision.show_camera_active_indicator`, and a `logging` block (`level`, `log_raw_speech`, `session_id_prefix`) to match the privacy and traceability changes above.
8. **16_LOGGING_AND_AUDIT.md** — log fields updated to match the new action schema and to record which input channel won during voice/gesture overlap.

No breaking renames of existing tool/intent names — only additive fields and one clarified risk value.
