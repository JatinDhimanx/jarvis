# Command Router

## Pipeline

`raw input -> normalized input -> intent -> entities -> context -> risk -> route`

## Intent categories
- `SYSTEM_CONTROL`
- `APP_CONTROL`
- `WINDOW_CONTROL`
- `MOUSE_CONTROL`
- `KEYBOARD_CONTROL`
- `MEDIA_CONTROL`
- `FILE_OPERATION`
- `WEB_SEARCH`
- `WEB_AUTOMATION`
- `AI_QUERY`
- `MEMORY`
- `SETTINGS`
- `STATUS`
- `CONVERSATION`
- `UNKNOWN`

## Router rules
1. Resolve explicit commands before guessing.
2. Use current context for pronouns such as "this", "that", "it".
3. Ask for clarification when two interpretations are materially different.
4. Never convert uncertainty into a destructive action.
5. Prefer deterministic command handlers for known system operations.

## Multi-modal conflict resolution
Voice and gesture can arrive close together in time. Rules:
1. An emergency signal always wins, regardless of source: spoken "stop"/"cancel" or open-palm `STOP` immediately overrides any in-flight or queued command from either channel.
2. If voice and gesture produce two different non-emergency intents within the same debounce window (default 500ms, see `04_GESTURE_ENGINE.md`), treat the more recent, higher-confidence input as authoritative and discard the other; do not merge them into one plan.
3. If both inputs resolve to the *same* intent (e.g. saying "pause" while pinching pause), execute once, not twice.
4. Log which channel supplied the winning input for every ambiguous overlap (see `16_LOGGING_AND_AUDIT.md`).

## Intent -> Action group mapping
Every intent must resolve to one or more concrete action-engine functions (see `08_ACTION_ENGINE.md`). This table is the single source of truth for that mapping; keep it in sync when either file changes.

| Intent | Action group(s) | Typical functions |
|---|---|---|
| `SYSTEM_CONTROL` | System | `set_volume`, `mute`, `set_brightness`, `lock_screen`, `shutdown` |
| `APP_CONTROL` | Application | `open_app`, `close_app`, `restart_app` |
| `WINDOW_CONTROL` | Window | `focus_window`, `minimize_window`, `maximize_window`, `switch_window` |
| `MOUSE_CONTROL` | Input | `move_mouse`, `click`, `double_click`, `scroll` |
| `KEYBOARD_CONTROL` | Input | `type_text`, `press_key`, `hotkey` |
| `MEDIA_CONTROL` | Media | `play_pause`, `next_track`, `previous_track` |
| `FILE_OPERATION` | Files | `open_file`, `create_file`, `move_file`, `copy_file`, `delete_file` |
| `WEB_SEARCH` | Online tool | `search_web` (see `09_TOOL_REGISTRY.md`) |
| `WEB_AUTOMATION` | Online tool | browser-automation tools, authorized only |
| `AI_QUERY` | Brain layer | local or online LLM call, no direct action |
| `MEMORY` | Memory | `READ`, `WRITE`, `UPDATE`, `FORGET` (see `03_CONTEXT_AND_MEMORY.md`) |
| `SETTINGS` | Config | read/update `17_CONFIG_SCHEMA.md` values |
| `STATUS` | Read-only | state/tool/health query, no side effect |
| `CONVERSATION` | Response only | no action, `13_RESPONSE_STYLE.md` applies |
| `UNKNOWN` | None | ask for clarification, never guess a mapping |

If an intent has no listed function for the requested entity, the router must not fabricate one — fall through to `AI_QUERY` for reasoning or ask the user.

## Example

User: "Open Chrome and search for Python decorators."

Result:
```json
{
  "intent": "WEB_SEARCH",
  "entities": {
    "application": "Chrome",
    "query": "Python decorators"
  },
  "plan": ["open_app", "search_web"]
}
```
