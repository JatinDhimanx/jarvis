# Voice Engine

## Pipeline
`microphone -> VAD -> wake word -> STT -> normalization -> router`

## Offline
Use a local speech recognition model such as Whisper/faster-whisper where hardware allows.

## Online
Optionally use a cloud speech service when enabled.

## Wake word
Configurable, default concept: "Jarvis".

## Privacy default
Microphone capture starts in an off/idle state on launch unless the user has explicitly enabled always-listen mode in config. Continuous audio is not buffered or transmitted online; only the segment following wake-word detection is processed. Active listening must be shown in the UI/HUD state (see `15_STATE_MACHINE.md`).

## Rules
- Ignore speech outside the active listening window unless wake word is enabled.
- Distinguish user speech from TTS playback to avoid feedback loops.
- Show/listen state in UI.
- Stop listening after timeout when no speech is detected.
- Do not execute high-risk actions from voice alone when confirmation is required.

## TTS
JARVIS should speak concise responses:
- acknowledgement
- action
- result
- failure reason when needed
