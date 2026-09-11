# Configuration Schema

Suggested configuration:

```yaml
jarvis:
  name: JARVIS
  wake_word: jarvis
  language: en-IN

mode:
  offline_enabled: true
  online_enabled: true
  prefer_offline: true

vision:
  enabled: false          # opt-in; camera stays off until explicitly enabled
  camera_index: 0
  gesture_confidence: 0.85
  cooldown_ms: 500
  show_camera_active_indicator: true

voice:
  enabled: true
  always_listen: false   # if false, mic is idle until wake word detection window opens
  wake_word_enabled: true
  silence_timeout_ms: 2500

safety:
  require_confirmation_for_medium: true
  require_confirmation_for_high: true

ui:
  hud_enabled: true
  show_gesture_feedback: true

memory:
  persistent_enabled: true

logging:
  level: INFO             # DEBUG | INFO | WARNING | ERROR | SECURITY
  log_raw_speech: false   # never log recognized text content unless true and user-acknowledged
  session_id_prefix: "s-"
```

All values should be validated at startup. `vision.enabled` and `voice.always_listen` default to the least-invasive setting; the user must explicitly opt in.
