# Memory Schema

Persistent memory is structured, minimal, and user-controlled.

## Example
```json
{
  "key": "preferred_browser",
  "value": "Chrome",
  "category": "preference",
  "source": "user",
  "confidence": 1.0,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

## Categories
- `preference`
- `workflow`
- `device`
- `project`
- `tool_configuration`

Do not store credentials or secrets.

## Lifecycle
`candidate -> authorized -> active -> outdated`

The current instruction always wins over stored preference.
