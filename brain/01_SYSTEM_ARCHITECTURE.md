# System Architecture

## Layers

1. **Input Layer**
   - microphone
   - webcam
   - keyboard/mouse
   - future sensors

2. **Perception Layer**
   - speech-to-text
   - hand landmark detection
   - gesture classification
   - input confidence

3. **Brain Layer**
   - intent detection
   - entity extraction
   - context resolution
   - planning
   - policy checks

4. **Execution Layer**
   - OS actions
   - application control
   - browser/web tools
   - file tools
   - APIs

5. **Output Layer**
   - text
   - text-to-speech
   - UI/HUD
   - action status

## Design rules
- Keep perception separate from intent.
- Keep planning separate from execution.
- Every executable action has a typed schema.
- Every action returns status: `success | failed | cancelled | blocked | needs_confirmation`.
- Every important action should be verifiable.
- Network availability is a capability, not a dependency.

## Hybrid decision
Use local deterministic logic first for:
- opening apps
- volume
- brightness
- media controls
- mouse/keyboard
- local files
- simple system queries

Use AI/online tools for:
- ambiguous natural-language requests
- research
- current information
- complex reasoning
- external services

If online capability fails, downgrade gracefully to offline functionality.
