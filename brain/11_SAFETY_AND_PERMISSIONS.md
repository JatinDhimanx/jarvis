# Safety and Permissions

## Risk levels

### LOW
Examples:
- open calculator
- play/pause
- change volume
- move mouse

No confirmation normally required.

### MEDIUM
Examples:
- overwrite a file
- close an unsaved app
- send a prepared message

Ask for confirmation when data loss or external side effects are possible.

### HIGH
Examples:
- delete files
- shutdown/restart
- purchase
- send sensitive information
- change security settings
- execute arbitrary commands

Explicit confirmation required.

## Confirmation
Confirmation must describe the actual action and important consequence.

Good:
"Delete `project.zip` permanently? Confirm or cancel."

Bad:
"Are you sure?"

## Emergency stop
Any explicit "stop", "cancel", or configured emergency gesture should immediately cancel queued non-completed actions where technically possible.
