# Logging and Audit

## Log levels
- DEBUG
- INFO
- WARNING
- ERROR
- SECURITY

## Log
- `session_id`, `action_id`, `source_event_id` (see `08_ACTION_ENGINE.md`)
- input type / source channel (voice, gesture, keyboard, ai_plan)
- recognized intent
- selected tool
- risk decision and confirmation outcome
- action result and `error_code` when applicable (see `14_ERROR_RECOVERY.md`)
- verification result
- which input channel won when voice/gesture overlapped (see `02_COMMAND_ROUTER.md`)

## Never log
- passwords
- API keys
- authentication tokens
- private message contents unless explicitly configured for debugging

## Example
```text
INFO session=s-8b21 action=a-2f9c1e source=voice intent=SET_VOLUME value=50
INFO session=s-8b21 action=a-2f9c1e tool=set_volume status=success verified=true error_code=null
```

Logs should support debugging without becoming a privacy risk.
