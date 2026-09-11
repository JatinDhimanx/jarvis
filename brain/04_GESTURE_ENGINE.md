# Gesture Engine

## Purpose
Convert camera observations into high-confidence semantic events.

## Recommended stack
- OpenCV for camera frames.
- MediaPipe Hand Landmarker or equivalent for hand landmarks.
- A classifier/state machine for gestures.
- Temporal smoothing to prevent accidental triggers.

## Canonical gestures

| Gesture | Semantic event | Default risk |
|---|---|---|
| Open palm | `STOP_OR_PAUSE` | Low |
| Pinch | `SELECT_OR_CLICK` | Low |
| Index point | `POINTER_MODE` | Low |
| Two fingers | `SCROLL_MODE` | Low |
| Swipe left | `PREVIOUS` | Low |
| Swipe right | `NEXT` | Low |
| Thumbs up | `CONFIRM` | Low |
| Thumbs down | `CANCEL` | Low |
| Fist | `STOP` | Low |

Note: "Default risk" above is the risk of *recognizing the gesture itself* (e.g. false positive triggers an unwanted click), not the risk of whatever action the gesture confirms or triggers. `CONFIRM` is itself a low-risk event even though the action it unblocks (e.g. `delete_file`) may be HIGH risk under `11_SAFETY_AND_PERMISSIONS.md`. Never derive an action's risk level from the gesture that invoked it — always use the risk level declared on the action/tool itself.

## Confidence rules
- Do not execute commands below configured confidence threshold.
- Require temporal stability for gestures with side effects.
- Use cooldown/debounce after each gesture.
- Provide visual feedback for recognized gestures.

## Gesture event schema
```json
{
  "type": "gesture",
  "name": "PINCH",
  "confidence": 0.94,
  "hand": "right",
  "timestamp": 0,
  "duration_ms": 180
}
```

## Privacy default
Camera capture is opt-in, off by default until the user explicitly enables gesture control in config. Frames are processed locally for landmark/gesture extraction and are not stored or transmitted unless the user explicitly enables a debug/recording mode. Camera-active state must be visibly indicated in the UI/HUD whenever the feed is live.

## Safety
Open-palm STOP must have priority over normal gesture commands.
