---
name: architecture
description: Architecture boundaries and dependency direction.
paths:
  - "src/**/*.ts"
  - "src/**/*.tsx"
  - "app/**/*.ts"
  - "app/**/*.tsx"
---

# Architecture Rules

- Preserve existing module boundaries.
- Document the dependency direction before introducing any cross-layer import.
- Keep domain logic independent from transport, UI, and persistence details.
- Add integration tests when changing cross-boundary behavior.
