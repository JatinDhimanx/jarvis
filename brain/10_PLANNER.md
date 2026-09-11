# Planner

## Purpose
Break complex requests into safe, ordered actions.

Example:
"Open VS Code, create a Python file, and write hello world."

Plan:
1. `open_app(VS Code)`
2. wait/verify window
3. `create_file(...)`
4. `open_file(...)`
5. `type_text(...)`
6. verify

## Planning rules
- Minimize unnecessary steps.
- Prefer reversible operations.
- Insert verification after important actions.
- Stop when a prerequisite fails.
- Ask for confirmation before a high-risk step.
- Do not continue blindly after unexpected UI state.

## Plan states
`DRAFT -> VALIDATED -> EXECUTING -> VERIFYING -> COMPLETE`

Failure:
`EXECUTING -> RECOVERY -> RETRY | ABORT`
