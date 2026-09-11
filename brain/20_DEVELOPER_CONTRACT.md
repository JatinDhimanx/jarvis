# Developer / AI Agent Contract

Any AI agent or developer modifying JARVIS must follow these rules.

## 1. Preserve boundaries
Do not merge perception, reasoning, policy, and execution into one uncontrolled function.

## 2. Structured outputs
Models produce structured intents/actions, never direct arbitrary OS commands.

## 3. Safety first
Every new tool declares risk, permissions, reversibility, and verification.

## 4. Offline support
Do not make internet mandatory for features that can reasonably operate locally.

## 5. Truthfulness
Never claim a tool executed successfully without a result or verification signal.

## 6. Backward compatibility
Avoid breaking existing command names/schemas without migration.

## 7. Testing
For each new action add:
- happy-path test
- invalid-input test
- permission test
- failure/recovery test
- confirmation test when relevant

## 8. Documentation
Update the relevant `.md` file whenever behavior, schema, or safety policy changes.

## 9. Secrets
Never hard-code credentials or commit secret material.

## 10. User control
The user remains the final authority over persistent preferences, permissions, and high-impact actions.
