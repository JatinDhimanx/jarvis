# Action Engine

## Purpose
Execute validated commands against the computer.

## Action groups

### Application
- `open_app`
- `close_app`
- `restart_app`

### Window
- `focus_window`
- `minimize_window`
- `maximize_window`
- `switch_window`

### Input
- `move_mouse`
- `click`
- `double_click`
- `scroll`
- `type_text`
- `press_key`
- `hotkey`

### System
- `set_volume`
- `mute`
- `set_brightness`
- `lock_screen`
- `shutdown` (high risk)

### Media
- `play_pause`
- `next_track`
- `previous_track`

### Files
- `open_file`
- `create_file`
- `move_file`
- `copy_file`
- `delete_file` (high risk)

## Contract
Every action:
```json
{
  "action_id": "a-2f9c1e",
  "session_id": "s-8b21",
  "source_event_id": "g-771a",
  "source": "voice | gesture | keyboard | ai_plan",
  "timestamp": "ISO-8601",
  "action": "set_volume",
  "parameters": {"value": 50},
  "risk": "low",
  "requires_confirmation": false
}
```
- `action_id` is unique per action call and is what logs, verification results, and error reports key off of.
- `session_id` groups all actions in one JARVIS run/session.
- `source_event_id` links back to the originating voice/gesture/text event for traceability (see `04_GESTURE_ENGINE.md`, `05_VOICE_ENGINE.md`).
- `requires_confirmation` is never set ad hoc by the model; it is derived deterministically from `risk` plus the `safety.require_confirmation_for_medium` / `require_confirmation_for_high` config flags (see `17_CONFIG_SCHEMA.md`, `11_SAFETY_AND_PERMISSIONS.md`). The action engine recomputes and validates this value itself rather than trusting an upstream claim.

Return:
```json
{
  "action_id": "a-2f9c1e",
  "status": "success",
  "action": "set_volume",
  "result": "Volume set to 50%",
  "verified": true,
  "error_code": null
}
```
`error_code` is populated (see `14_ERROR_RECOVERY.md` for the code list) whenever `status` is `failed` or `blocked`.

## Rule
The action engine executes only validated structured actions. It never executes raw model-generated shell/code directly.
