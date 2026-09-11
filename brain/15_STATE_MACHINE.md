# Runtime State Machine

## States
- `IDLE`
- `LISTENING`
- `THINKING`
- `WAITING_CONFIRMATION`
- `EXECUTING`
- `VERIFYING`
- `ERROR`
- `STOPPED`

## Normal flow
`IDLE -> LISTENING -> THINKING -> EXECUTING -> VERIFYING -> IDLE`

Confirmation:
`THINKING -> WAITING_CONFIRMATION -> EXECUTING`

Cancellation:
`WAITING_CONFIRMATION -> IDLE`

Emergency:
`ANY -> STOPPED -> IDLE`

## State requirements
The UI should expose current state.
The brain must not accept conflicting execution requests while a non-interruptible action is running.
