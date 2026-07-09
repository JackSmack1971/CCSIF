---
name: testing
description: Testing expectations for source changes.
globs:
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
- Avoid mocking the source of truth when the purpose is state verification.
