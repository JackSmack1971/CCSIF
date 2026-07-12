---
paths:
  - ".claude/**"
  - "CLAUDE.md"
  - "CLAUDE.local.md"
  - "AGENTS.md"
  - "README.md"
  - "CONTRIBUTING.md"
  - "SECURITY.md"
  - ".github/**"
---

# Karpathy Guidelines

Delta to `surgical-density.md` (smallest-change, verify-before-done, solution
ladder) and `constitutional-agent-engineering-rules.md`; do not re-derive
those rules here.

- State assumptions explicitly before writing code, not after; an unstated
  assumption is a defect even if the code happens to work.
- Define the verification target before declaring a task finished, not after
  the diff exists.
- Keep the agent on a leash: small incremental chunks, one generate-then-
  verify cycle at a time, never a large unverified batch of changes.
- For optimization or tuning work, use a metric-gated experiment loop: a
  single named metric, a fixed budget, keep the change only if the metric
  improved, revert otherwise. Never claim improvement without that loop.
