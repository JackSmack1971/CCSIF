---
paths:
  - "**/*"
---
# Failure Escalation Protocol

When the same failing command or same error signature repeats after two targeted repair attempts, stop editing and escalate.

## Required Escalation Payload

- Exact failing command
- Raw stdout and stderr
- Files changed in the attempted fix
- Current hypothesis about the root cause
- What was retried and why it still failed

## Escalation Target

- Open or update a GitHub issue in this repository.
- Assign the issue to the current agent if appropriate.
- Add a comment containing the required escalation payload.
- Link the current failing command or run artifact if one exists.

## Stop Condition

- No more than two same-failure retries.
- After the second repeat, pause local edits and record the issue or handoff before continuing.
