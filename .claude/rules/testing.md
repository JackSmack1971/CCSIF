---
name: testing
description: Testing expectations for source changes.
paths:
  - "src/**"
  - "test/**"
  - "tests/**"
  - "**/*.spec.*"
  - "**/*.test.*"
---

# Testing Rules

- Start with the smallest test that proves the behavior.
- Add regression tests for confirmed bugs.
- Keep tests deterministic.
- Exercise the real source of truth directly when the test's purpose is state verification.
