# Error Recovery

## Error classes and codes
Stable codes so logs, UI, and TTS responses can reference errors consistently. Do not renumber existing codes when adding new ones — append.

| Code | Class | Meaning |
|---|---|---|
| `E100` | input error | malformed or unrecognized raw input |
| `E200` | perception error | STT/gesture confidence below threshold or sensor failure |
| `E300` | routing error | intent could not be resolved to a known action group |
| `E400` | tool unavailable | requested tool not registered or disabled for current mode |
| `E410` | permission denied | required OS/user permission missing |
| `E420` | confirmation denied | user rejected a required confirmation |
| `E500` | timeout | action or tool call exceeded its time budget |
| `E510` | unexpected UI state | target app/window not in the expected state to proceed |
| `E600` | network failure | online capability required but unreachable |
| `E700` | verification failure | action executed but post-check did not confirm success |

## Recovery
1. Detect.
2. Stop dependent actions.
3. Retry only if safe and idempotent.
4. Re-check state.
5. Offer a clear fallback.

## Example
If `open_app` times out:
- check whether app actually opened;
- if yes, continue;
- if no, retry once;
- if still failed, report failure.

Never loop indefinitely.
